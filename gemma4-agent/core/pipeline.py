"""
Supervisor & Pipeline Orchestrator enforcing:
    UNDERSTAND -> LOCALIZE -> PLAN -> PATCH -> VALIDATE -> LEARN
with every architectural capability switchable via `config/experiment.yaml`.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List

from core.config_loader import load_experiment_config
from core.model_client import Gemma4ModelClient
from core.schemas import PlanArtifact
from core.agents import (
    FunctionSummarizerAgent,
    BugLookupAgent,
    ResearcherAgent,
    PlannerAgent,
    CoderAgent,
    ValidatorAgent,
    FailureAnalyzerAgent,
)
from tools.repo_tools import RepositoryAnalyzer
from tools.graph_tools import FlowGraphBuilder
from tools.bug_db import LocalBugDatabase
from tools.evaluation_tools import (
    StructuredLogger,
    TaskComplexityEstimator,
    TimeBudgetManager,
    ContextBudgetManager,
    TestRunnerTool,
)

DEFAULT_ISSUE = (
    "Users are charged the full amount even when a valid discount coupon is supplied."
)


class Gemma4AgentPipeline:
    def __init__(
        self,
        agent_root: Path,
        experiment: Optional[str] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
    ):
        self.agent_root = Path(agent_root).resolve()
        self.config = load_experiment_config(self.agent_root, experiment)
        if config_overrides:
            for section, vals in config_overrides.items():
                if isinstance(vals, dict) and isinstance(self.config.get(section), dict):
                    self.config[section].update(vals)
                else:
                    self.config[section] = vals

        self.experiment_id: str = str(self.config.get("experiment_id", "CUSTOM"))
        self.model_client = Gemma4ModelClient(self.config)
        self.complexity_estimator = TaskComplexityEstimator(self.config)
        self.time_manager = TimeBudgetManager(self.config)
        self.context_manager = ContextBudgetManager(self.config)

    def run_task(
        self,
        issue_text: str = DEFAULT_ISSUE,
        source_repo_path: Optional[Path] = None,
        demonstrate_failure_recovery: bool = False,
    ) -> Dict[str, Any]:
        src_repo = (
            Path(source_repo_path).resolve()
            if source_repo_path
            else (self.agent_root / "sample_repo")
        )
        work_dir = Path(tempfile.mkdtemp(prefix=f"gemma4_task_{self.experiment_id}_"))
        work_repo = work_dir / "repo"
        shutil.copytree(src_repo, work_repo)

        knowledge_dir = self.agent_root / "repository_knowledge"
        log_file = knowledge_dir / "logger_state.json"

        try:
            logger = StructuredLogger(
                task_description=issue_text,
                experiment_id=self.experiment_id,
                config=self.config,
                log_file=log_file,
            )
            repo_analyzer = RepositoryAnalyzer(
                repo_path=work_repo,
                knowledge_dir=knowledge_dir,
                config=self.config,
            )
            flow_builder = FlowGraphBuilder(knowledge_dir=knowledge_dir)
            bug_db = LocalBugDatabase(
                db_path=self.agent_root / "knowledge" / "bug_db" / "seed_bugs.json"
            )
            test_runner = TestRunnerTool(repo_path=work_repo)

            summarizer = FunctionSummarizerAgent(repo_analyzer, flow_builder, self.config)
            bug_lookup_agent = BugLookupAgent(bug_db, self.config)
            researcher = ResearcherAgent(self.config)
            planner = PlannerAgent(self.model_client, self.config)
            coder = CoderAgent(self.model_client, repo_analyzer, self.config)
            validator = ValidatorAgent(test_runner, self.config)
            failure_analyzer = FailureAnalyzerAgent(self.model_client, self.config)

            arch = self.config.get("architecture", {})
            phase_trace: List[str] = []

            # PHASE 1: UNDERSTAND
            logger.set_phase("understand")
            phase_trace.append("UNDERSTAND")
            understand_out = summarizer.run(logger=logger)
            knowledge = understand_out["knowledge"]
            flow_graph = understand_out["flow_graph"]

            flow_depth = max(
                (len(chain) for chain in flow_graph.get("execution_flows", {}).values()),
                default=1,
            )
            dep_count = sum(
                len(m.get("imports", [])) for m in knowledge.get("modules", {}).values()
            )
            complexity = self.complexity_estimator.estimate(
                issue_text=issue_text,
                relevant_file_count=len(knowledge.get("modules", {})),
                flow_depth=flow_depth,
                test_count=len(knowledge.get("tests", [])),
                dependency_count=dep_count,
            )
            time_budget = self.time_manager.allocate_for_tier(complexity["tier"])
            logger.set_budgets(complexity=complexity, time_budget=time_budget)

            initial_test_check = test_runner.run_targeted_test(
                "test_checkout_applies_coupon"
            )
            logger.record_test_run(
                {**initial_test_check, "scope": "pre_patch_reproduction"}
            )

            # PHASE 2: LOCALIZE
            logger.set_phase("localize")
            phase_trace.append("LOCALIZE")
            candidate_functions = [
                f["function"] for f in knowledge.get("functions", [])
            ]
            bug_matches = bug_lookup_agent.run(
                issue_text=issue_text,
                candidate_functions=candidate_functions,
                logger=logger,
            )
            research_out = researcher.run(
                issue_text=issue_text,
                knowledge=knowledge,
                flow_graph=flow_graph,
                bug_matches=bug_matches,
                logger=logger,
            )

            # PHASE 3, 4, 5, 6: PLAN -> PATCH -> VALIDATE -> LEARN
            max_repairs = int(
                self.config.get("validation", {}).get("max_repair_iterations", 3)
            )
            if not arch.get("use_failure_analyzer", True):
                max_repairs = 1

            prior_failure: Optional[Dict[str, Any]] = None
            final_plan: Optional[PlanArtifact] = None
            final_patch_info: Dict[str, Any] = {}
            final_validation: Dict[str, Any] = {}
            failure_analyses: List[Dict[str, Any]] = []
            iterations_executed = 0

            for attempt in range(1, max_repairs + 1):
                iterations_executed = attempt

                # PLAN
                logger.set_phase("plan")
                phase_trace.append("PLAN")
                if arch.get("use_planner", True):
                    final_plan = planner.run(
                        issue_text=issue_text,
                        knowledge=knowledge,
                        flow_graph=flow_graph,
                        bug_matches=bug_matches,
                        research=research_out,
                        prior_failure=prior_failure,
                        context_mgr=self.context_manager,
                        logger=logger,
                    )
                else:
                    final_plan = PlanArtifact(
                        problem=issue_text,
                        evidence=["Direct localization to pricing.py::calculate_price"],
                        root_cause_hypothesis="apply_discount result not subtracted from subtotal",
                        affected_functions=["calculate_price"],
                        expected_flow=["checkout", "calculate_price", "apply_discount"],
                        actual_flow=["checkout", "calculate_price"],
                        changes_required=["Subtract discount_amount in calculate_price"],
                        files_to_modify=["pricing.py"],
                        tests_to_run=["test_checkout_applies_coupon"],
                        risk=[],
                    )

                # PATCH
                logger.set_phase("patch")
                phase_trace.append("PATCH")
                simulate_fail = demonstrate_failure_recovery and (attempt == 1)
                final_patch_info = coder.run(
                    issue_text=issue_text,
                    plan=final_plan,
                    logger=logger,
                    simulate_incomplete_first_attempt=simulate_fail,
                )

                # VALIDATE
                logger.set_phase("validate")
                phase_trace.append("VALIDATE")
                targeted_name = (
                    final_plan.tests_to_run[0] if final_plan.tests_to_run else None
                )
                final_validation = validator.run(
                    targeted_test_name=targeted_name,
                    logger=logger,
                )

                if final_validation.get("passed"):
                    logger.set_phase("learn")
                    phase_trace.append("LEARN")
                    logger.set_phase("done")
                    break

                # LEARN / FAILURE ANALYZER
                logger.set_phase("learn")
                phase_trace.append("LEARN")
                if arch.get("use_failure_analyzer", True) and attempt < max_repairs:
                    fa_artifact = failure_analyzer.run(
                        validation_report=final_validation,
                        flow_graph=flow_graph,
                        logger=logger,
                    )
                    prior_failure = fa_artifact.to_dict()
                    failure_analyses.append(prior_failure)
                else:
                    break

            return {
                "experiment_id": self.experiment_id,
                "config_path": self.config.get("_config_path"),
                "principle_enforced": "UNDERSTAND -> LOCALIZE -> PLAN -> PATCH -> VALIDATE -> LEARN",
                "phase_sequence_executed": phase_trace,
                "passed": bool(final_validation.get("passed", False)),
                "iterations_executed": iterations_executed,
                "model_info": {
                    "model": self.model_client.model_name,
                    "temperature": self.model_client.temperature,
                    "lora_status": self.model_client.lora_status,
                },
                "complexity_estimate": complexity,
                "time_budget": time_budget,
                "pre_patch_reproduction": initial_test_check,
                "repository_knowledge_summary": {
                    "modules_count": len(knowledge.get("modules", {})),
                    "functions_count": len(knowledge.get("functions", [])),
                    "classes_count": len(knowledge.get("classes", [])),
                    "tests_count": len(knowledge.get("tests", [])),
                    "entry_points": flow_graph.get("entry_points", []),
                    "execution_flows": flow_graph.get("execution_flows", {}),
                    "detected_flow_anomalies": flow_graph.get(
                        "detected_flow_anomalies", []
                    ),
                },
                "bug_db_matches": bug_matches,
                "research_summary": research_out,
                "plan": final_plan.to_dict() if final_plan else None,
                "patch": final_patch_info.get("diff", ""),
                "patch_metadata": final_patch_info,
                "validation": final_validation,
                "failure_analyses": failure_analyses,
                "logger_state": logger.state.to_dict(),
            }
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
