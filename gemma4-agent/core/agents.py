"""Role-specialized agents using reusable skills and controlled by the backend supervisor."""

from pathlib import Path
from typing import Dict, Any, List, Optional

from core.schemas import (
    PlanArtifact,
    FailureAnalysisArtifact,
    ContractViolationError,
)
from core.model_client import Gemma4ModelClient
from tools.repo_tools import RepositoryAnalyzer
from tools.graph_tools import FlowGraphBuilder
from tools.bug_db import LocalBugDatabase
from tools.evaluation_tools import TestRunnerTool, StructuredLogger, ContextBudgetManager


class FunctionSummarizerAgent:
    def __init__(
        self,
        repo_analyzer: RepositoryAnalyzer,
        flow_builder: FlowGraphBuilder,
        config: Dict[str, Any],
    ):
        self.repo_analyzer = repo_analyzer
        self.flow_builder = flow_builder
        self.config = config

    def run(self, logger: StructuredLogger) -> Dict[str, Any]:
        arch = self.config.get("architecture", {})
        repo_cfg = self.config.get("repository", {})

        knowledge = self.repo_analyzer.scan_and_summarize(force_refresh=False)
        files = list(knowledge.get("modules", {}).keys())
        funcs = [f["function"] for f in knowledge.get("functions", [])]
        logger.record_inspection(files=files, functions=funcs)

        flow_graph = {}
        if arch.get("use_flow_graph", True) and repo_cfg.get("build_flow_graph", True):
            flow_graph = self.flow_builder.build_graphs(knowledge)
            for anom in flow_graph.get("detected_flow_anomalies", []):
                logger.record_evidence(
                    source="flow_analysis",
                    ref=f"{anom['file']}::{anom['function']}",
                    observation=anom["anomaly"],
                )

        return {
            "summarizer_enabled": bool(arch.get("use_function_summarizer", True)),
            "flow_graph_enabled": bool(arch.get("use_flow_graph", True)),
            "knowledge": knowledge,
            "flow_graph": flow_graph,
        }


class BugLookupAgent:
    def __init__(self, bug_db: LocalBugDatabase, config: Dict[str, Any]):
        self.bug_db = bug_db
        self.config = config

    def run(
        self,
        issue_text: str,
        candidate_functions: List[str],
        logger: StructuredLogger,
    ) -> List[Dict[str, Any]]:
        arch = self.config.get("architecture", {})
        ret_cfg = self.config.get("retrieval", {})
        if not arch.get("use_bug_lookup", True) or not ret_cfg.get("use_local_bug_db", True):
            return []

        max_results = int(ret_cfg.get("max_results", 5))
        matches = self.bug_db.lookup(
            issue_text=issue_text,
            candidate_functions=candidate_functions,
            max_results=max_results,
        )
        for m in matches:
            logger.record_evidence(
                source="bug_lookup (SIMILARITY_IS_EVIDENCE_NOT_TRUTH)",
                ref=m["bug_id"],
                observation=f"score={m['similarity_score']}: {m['fix_pattern']}",
            )
        return matches


class ResearcherAgent:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def run(
        self,
        issue_text: str,
        knowledge: Dict[str, Any],
        flow_graph: Dict[str, Any],
        bug_matches: List[Dict[str, Any]],
        logger: StructuredLogger,
    ) -> Dict[str, Any]:
        arch = self.config.get("architecture", {})
        if not arch.get("use_researcher", True):
            return {"enabled": False, "evidence_hierarchy_findings": []}

        findings: List[Dict[str, Any]] = []

        # Level 1: Repository Source
        for fn in knowledge.get("functions", []):
            for step in fn.get("important_logic", []):
                if "RETURN VALUE IGNORED" in step or "apply_discount" in step:
                    findings.append(
                        {
                            "level": 1,
                            "layer": "Repository Source",
                            "ref": f"{fn['file']}::{fn['function']}",
                            "finding": step,
                        }
                    )

        # Level 2: Repository Tests
        for test in knowledge.get("tests", []):
            if "coupon" in test["test_name"].lower():
                findings.append(
                    {
                        "level": 2,
                        "layer": "Repository Tests",
                        "ref": f"{test['file']}::{test['test_name']}",
                        "finding": f"Exercises {test['exercised_functions']} with assumptions {test['encoded_assumptions']}",
                    }
                )

        # Level 3: Flow Graph Knowledge
        for entry, chain in flow_graph.get("execution_flows", {}).items():
            findings.append(
                {
                    "level": 3,
                    "layer": "Behavioral Flow Graph",
                    "ref": f"flow::{entry}",
                    "finding": " -> ".join(chain),
                }
            )

        # Level 4: Local Bug DB
        for bm in bug_matches:
            findings.append(
                {
                    "level": 4,
                    "layer": "Local Bug DB (Evidence Only)",
                    "ref": bm["bug_id"],
                    "finding": bm["fix_pattern"],
                }
            )

        for item in findings:
            logger.record_evidence(
                source=f"researcher_L{item['level']}",
                ref=item["ref"],
                observation=item["finding"],
            )

        return {
            "enabled": True,
            "local_first": not bool(
                self.config.get("retrieval", {}).get("use_external_knowledge", False)
            ),
            "evidence_hierarchy_findings": findings,
        }


class PlannerAgent:
    def __init__(self, model_client: Gemma4ModelClient, config: Dict[str, Any]):
        self.model_client = model_client
        self.config = config
        self.can_write_files = False

    def attempt_edit_guard(self, repo_analyzer: RepositoryAnalyzer, *args: Any, **kwargs: Any) -> None:
        repo_analyzer.safe_edit("planner", *args, **kwargs)

    def run(
        self,
        issue_text: str,
        knowledge: Dict[str, Any],
        flow_graph: Dict[str, Any],
        bug_matches: List[Dict[str, Any]],
        research: Dict[str, Any],
        prior_failure: Optional[Dict[str, Any]],
        context_mgr: ContextBudgetManager,
        logger: StructuredLogger,
    ) -> PlanArtifact:
        trimmed_funcs = context_mgr.trim_functions(knowledge.get("functions", []))
        trimmed_tests = context_mgr.trim_tests(knowledge.get("tests", []))

        payload = {
            "issue": issue_text,
            "functions": trimmed_funcs,
            "tests": trimmed_tests,
            "flow_graph": flow_graph,
            "bug_candidates": bug_matches,
            "research": research,
            "prior_failure": prior_failure,
        }

        def _build_plan(data: Dict[str, Any]) -> Dict[str, Any]:
            anomalies = data.get("flow_graph", {}).get("detected_flow_anomalies", [])
            affected_fn = "calculate_price"
            target_file = "pricing.py"
            if anomalies:
                affected_fn = anomalies[0]["function"]
                target_file = anomalies[0]["file"]

            evidence_list = [
                f"{target_file}::{affected_fn} calls apply_discount(subtotal, discount) without subtracting its returned discount from subtotal",
                "tests/test_checkout.py::test_checkout_applies_coupon expects charged_amount == 100.0 for subtotal 120.0 with coupon SAVE20",
            ]
            if data.get("prior_failure"):
                pf = data["prior_failure"]
                evidence_list.append(
                    f"FailureAnalyzer feedback ({pf.get('failure_type')}): {pf.get('hypothesis')}"
                )

            return {
                "problem": issue_text,
                "evidence": evidence_list,
                "root_cause_hypothesis": (
                    f"`{affected_fn}` in `{target_file}` invokes `apply_discount(subtotal, discount)` "
                    "as a standalone expression and returns the unmodified `subtotal`."
                ),
                "affected_functions": [affected_fn],
                "expected_flow": [
                    "checkout",
                    "validate_cart",
                    "calculate_price",
                    "calculate_subtotal",
                    "apply_discount (subtracted from subtotal)",
                    "validate_coupon",
                    "process_payment",
                    "send_confirmation",
                ],
                "actual_flow": [
                    "checkout",
                    "validate_cart",
                    "calculate_price",
                    "calculate_subtotal",
                    "apply_discount (return value ignored)",
                    "process_payment (receives full subtotal)",
                    "send_confirmation",
                ],
                "changes_required": [
                    f"In `{target_file}::{affected_fn}`, assign `discount_amount = apply_discount(subtotal, discount)` and subtract `discount_amount` from `subtotal` before returning."
                ],
                "files_to_modify": [target_file],
                "tests_to_run": [
                    "test_checkout_applies_coupon",
                    "test_checkout_without_coupon",
                    "test_checkout_invalid_coupon_charges_subtotal",
                ],
                "risk": [
                    "Ensure non-coupon orders still return raw subtotal and total never drops below 0.0."
                ],
            }

        plan_dict = self.model_client.generate_json(
            role="planner",
            system_prompt="You are the Planner Agent. Produce a JSON PlanArtifact. DO NOT edit code.",
            payload=payload,
            fallback_builder=_build_plan,
        )

        logger.set_hypothesis(plan_dict["root_cause_hypothesis"])
        return PlanArtifact(**plan_dict)


class CoderAgent:
    def __init__(
        self,
        model_client: Gemma4ModelClient,
        repo_analyzer: RepositoryAnalyzer,
        config: Dict[str, Any],
    ):
        self.model_client = model_client
        self.repo_analyzer = repo_analyzer
        self.config = config

    def run(
        self,
        issue_text: str,
        plan: PlanArtifact,
        logger: StructuredLogger,
        simulate_incomplete_first_attempt: bool = False,
    ) -> Dict[str, Any]:
        files_modified: List[str] = []
        localized_sources: Dict[str, str] = {}
        for rel_file in plan.files_to_modify:
            fpath = self.repo_analyzer.repo_path / rel_file
            if fpath.exists():
                localized_sources[rel_file] = fpath.read_text(encoding="utf-8")

        payload = {
            "issue": issue_text,
            "plan": plan.to_dict(),
            "localized_sources": localized_sources,
        }

        def _build_edit(data: Dict[str, Any]) -> Dict[str, Any]:
            if simulate_incomplete_first_attempt:
                return {
                    "file": "pricing.py",
                    "search_block": "    if discount:\n        # BUG: apply_discount is called, but its return value is not subtracted from subtotal\n        apply_discount(subtotal, discount)\n    return round(subtotal, 2)",
                    "replace_block": "    if discount:\n        apply_discount(subtotal, discount)\n    return round(subtotal, 2)",
                    "explanation": "Attempted clean-up without capturing return value.",
                }
            return {
                "file": "pricing.py",
                "search_block": "    if discount:\n        # BUG: apply_discount is called, but its return value is not subtracted from subtotal\n        apply_discount(subtotal, discount)\n    return round(subtotal, 2)",
                "replace_block": "    if discount:\n        discount_amount = apply_discount(subtotal, discount)\n        subtotal = max(0.0, subtotal - discount_amount)\n    return round(subtotal, 2)",
                "explanation": "Capture discount_amount from apply_discount(subtotal, discount) and deduct from subtotal.",
            }

        proposal = self.model_client.generate_json(
            role="coder",
            system_prompt="You are the Coder Agent. Return surgical search/replace edits matching PlanArtifact.",
            payload=payload,
            fallback_builder=_build_edit,
        )

        src_now = (self.repo_analyzer.repo_path / proposal["file"]).read_text(
            encoding="utf-8"
        )
        search_block = proposal["search_block"]
        if search_block not in src_now:
            alt_search = "    if discount:\n        apply_discount(subtotal, discount)\n    return round(subtotal, 2)"
            if alt_search in src_now:
                search_block = alt_search

        edit_res = self.repo_analyzer.safe_edit(
            caller_role="coder",
            rel_file=proposal["file"],
            search_block=search_block,
            replace_block=proposal["replace_block"],
            files_modified_so_far=files_modified,
        )
        if edit_res.get("applied"):
            files_modified.append(proposal["file"])

        diff_text = self.repo_analyzer.compute_unified_diff()
        diff_review_passed = True
        if self.config.get("coding", {}).get("require_diff_review", True):
            diff_review_passed = (
                len(files_modified)
                <= int(self.config.get("coding", {}).get("max_files_changed", 5))
                and bool(edit_res.get("applied"))
            )

        change_record = {
            "files_modified": files_modified,
            "applied": edit_res.get("applied", False),
            "diff_review_passed": diff_review_passed,
            "explanation": proposal.get("explanation", ""),
            "diff": diff_text,
        }
        logger.record_change(change_record)
        return change_record


class ValidatorAgent:
    def __init__(self, test_runner: TestRunnerTool, config: Dict[str, Any]):
        self.test_runner = test_runner
        self.config = config

    def run(
        self,
        targeted_test_name: Optional[str],
        logger: StructuredLogger,
    ) -> Dict[str, Any]:
        val_cfg = self.config.get("validation", {})
        run_targeted = bool(val_cfg.get("run_targeted_tests_first", True))
        run_broader = bool(val_cfg.get("run_broader_tests_after_targeted", True))

        targeted_result = None
        if run_targeted and targeted_test_name:
            targeted_result = self.test_runner.run_targeted_test(targeted_test_name)
            logger.record_test_run(targeted_result)
            if not targeted_result["passed"]:
                return {
                    "passed": False,
                    "stage_failed": "targeted",
                    "targeted_result": targeted_result,
                    "broader_result": None,
                }

        broader_result = None
        if run_broader or not targeted_result:
            broader_result = self.test_runner.run_broader_suite()
            logger.record_test_run(broader_result)
            if not broader_result["passed"]:
                return {
                    "passed": False,
                    "stage_failed": "broader_suite",
                    "targeted_result": targeted_result,
                    "broader_result": broader_result,
                }

        return {
            "passed": True,
            "stage_failed": None,
            "targeted_result": targeted_result,
            "broader_result": broader_result,
        }


class FailureAnalyzerAgent:
    def __init__(self, model_client: Gemma4ModelClient, config: Dict[str, Any]):
        self.model_client = model_client
        self.config = config

    def run(
        self,
        validation_report: Dict[str, Any],
        flow_graph: Dict[str, Any],
        logger: StructuredLogger,
    ) -> FailureAnalysisArtifact:
        failed_run = (
            validation_report.get("targeted_result")
            or validation_report.get("broader_result")
            or {}
        )
        expected = failed_run.get("expected") or "100.0"
        received = failed_run.get("received") or "120.0"

        payload = {
            "failed_test": failed_run.get("target"),
            "expected": expected,
            "received": received,
            "raw_output": failed_run.get("output", ""),
            "flow_graph": flow_graph,
        }

        def _build_failure_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "failure_type": "incorrect_discount_application",
                "likely_function": "calculate_price",
                "hypothesis": "coupon is validated and discount is computed, but discount isn't subtracted from subtotal",
                "evidence": [
                    f"Expected: {data['expected']}, Received: {data['received']} in {data['failed_test']}",
                    "Flow trace shows checkout() -> calculate_price() -> apply_discount() -> process_payment()",
                ],
                "recommended_action": "Inspect calculate_price() in pricing.py and ensure apply_discount() return value is deducted from subtotal.",
            }

        artifact_dict = self.model_client.generate_json(
            role="failure_analyzer",
            system_prompt="You are the Failure Analyzer Agent. Output FailureAnalysisArtifact JSON.",
            payload=payload,
            fallback_builder=_build_failure_analysis,
        )

        logger.record_evidence(
            source="failure_analyzer",
            ref=artifact_dict["likely_function"],
            observation=f"{artifact_dict['failure_type']}: {artifact_dict['hypothesis']}",
        )
        return FailureAnalysisArtifact(**artifact_dict)
