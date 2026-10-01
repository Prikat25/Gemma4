"""Validation test runner, task complexity estimator, time/context budget managers, and structured logger."""

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.schemas import LoggerState


class StructuredLogger:
    def __init__(self, task_description: str, experiment_id: str, config: Dict[str, Any], log_file: Optional[Path] = None):
        arch = config.get("architecture", {})
        self.enabled: bool = bool(arch.get("use_logger", True))
        self.log_file = log_file
        self.state = LoggerState(
            task=task_description,
            current_phase="understand",
            experiment_id=experiment_id,
            active_capabilities={k: bool(v) for k, v in arch.items()},
        )
        self._persist()

    def set_phase(self, phase: str) -> None:
        self.state.current_phase = phase
        self._persist()

    def set_hypothesis(self, hypothesis: str) -> None:
        self.state.hypothesis = hypothesis
        self._persist()

    def record_evidence(self, source: str, ref: str, observation: str) -> None:
        entry = {"source": source, "ref": ref, "observation": observation}
        if entry not in self.state.evidence:
            self.state.evidence.append(entry)
        self._persist()

    def record_inspection(self, files: List[str], functions: List[str]) -> None:
        for f in files:
            if f not in self.state.files_inspected:
                self.state.files_inspected.append(f)
        for fn in functions:
            if fn not in self.state.functions_inspected:
                self.state.functions_inspected.append(fn)
        self._persist()

    def record_test_run(self, result: Dict[str, Any]) -> None:
        self.state.tests_run.append(result)
        if not result.get("passed", False):
            self.state.failures.append(result)
        self._persist()

    def record_change(self, change_info: Dict[str, Any]) -> None:
        self.state.changes.append(change_info)
        self._persist()

    def set_budgets(self, complexity: Dict[str, Any], time_budget: Dict[str, Any]) -> None:
        self.state.complexity_estimate = complexity
        self.state.time_budget = time_budget
        self._persist()

    def _persist(self) -> None:
        if self.enabled and self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            self.log_file.write_text(
                json.dumps(self.state.to_dict(), indent=2), encoding="utf-8"
            )


class TaskComplexityEstimator:
    def __init__(self, config: Dict[str, Any]):
        weights = config.get("time", {}).get("complexity_weights", {})
        self.w_files = float(weights.get("relevant_file_count", 0.30))
        self.w_flow = float(weights.get("flow_depth", 0.25))
        self.w_tests = float(weights.get("test_count", 0.20))
        self.w_deps = float(weights.get("dependency_count", 0.15))
        self.w_issue = float(weights.get("issue_length", 0.10))

    def estimate(
        self,
        issue_text: str,
        relevant_file_count: int,
        flow_depth: int,
        test_count: int,
        dependency_count: int,
    ) -> Dict[str, Any]:
        issue_len_norm = min(10.0, len(issue_text.split()) / 15.0)
        score = round(
            self.w_files * relevant_file_count
            + self.w_flow * flow_depth
            + self.w_tests * test_count
            + self.w_deps * dependency_count
            + self.w_issue * issue_len_norm,
            3,
        )
        if score < 2.0:
            tier = "simple"
        elif score < 4.5:
            tier = "medium"
        else:
            tier = "complex"

        return {
            "complexity_score": score,
            "tier": tier,
            "inputs": {
                "relevant_file_count": relevant_file_count,
                "flow_depth": flow_depth,
                "test_count": test_count,
                "dependency_count": dependency_count,
                "issue_word_count": len(issue_text.split()),
            },
        }


class TimeBudgetManager:
    def __init__(self, config: Dict[str, Any]):
        time_cfg = config.get("time", {})
        self.total_budget_minutes = float(time_cfg.get("total_budget_minutes", 720))
        self.reserve_minutes = float(time_cfg.get("reserve_minutes", 60))
        self.allocations = time_cfg.get(
            "task_allocation", {"simple": 10, "medium": 20, "complex": 40}
        )
        self.start_ts = time.time()

    def allocate_for_tier(self, tier: str) -> Dict[str, Any]:
        minutes = float(self.allocations.get(tier, 20))
        elapsed_sec = round(time.time() - self.start_ts, 3)
        return {
            "total_competition_budget_minutes": self.total_budget_minutes,
            "reserve_minutes": self.reserve_minutes,
            "task_tier": tier,
            "allocated_task_minutes": minutes,
            "allocated_task_seconds": minutes * 60.0,
            "elapsed_seconds": elapsed_sec,
            "within_budget": elapsed_sec < (minutes * 60.0),
        }


class ContextBudgetManager:
    def __init__(self, config: Dict[str, Any]):
        ctx = config.get("context", {})
        self.max_function_summaries = int(ctx.get("max_function_summaries", 30))
        self.max_tests = int(ctx.get("max_tests", 10))
        self.max_flow_nodes = int(ctx.get("max_flow_nodes", 50))
        self.max_bug_matches = int(ctx.get("max_bug_matches", 5))
        self.max_research_results = int(ctx.get("max_research_results", 5))

    def trim_functions(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if self.max_function_summaries <= 0:
            return []
        return functions[: self.max_function_summaries]

    def trim_tests(self, tests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if self.max_tests <= 0:
            return []
        return tests[: self.max_tests]


class TestRunnerTool:
    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path).resolve()

    def run_targeted_test(self, test_method_name: Optional[str] = None) -> Dict[str, Any]:
        if test_method_name:
            cmd = [
                sys.executable,
                "-m",
                "unittest",
                f"tests.test_checkout.TestCheckoutFlow.{test_method_name}",
            ]
            target_label = f"tests/test_checkout.py::{test_method_name}"
        else:
            cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
            target_label = "tests/ (all)"

        return self._exec(cmd, target_label, scope="targeted")

    def run_broader_suite(self) -> Dict[str, Any]:
        cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
        return self._exec(cmd, "tests/ (full regression suite)", scope="broader_suite")

    def _exec(self, cmd: List[str], target_label: str, scope: str) -> Dict[str, Any]:
        t0 = time.time()
        proc = subprocess.run(
            cmd,
            cwd=str(self.repo_path),
            capture_output=True,
            text=True,
            timeout=30,
        )
        duration = round(time.time() - t0, 3)
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        passed = proc.returncode == 0

        expected_val = None
        received_val = None
        match = re.search(
            r"Expected:\s*([0-9.]+),\s*Received:\s*([0-9.]+)", output
        )
        if match:
            expected_val = match.group(1)
            received_val = match.group(2)

        return {
            "scope": scope,
            "target": target_label,
            "passed": passed,
            "exit_code": proc.returncode,
            "duration_seconds": duration,
            "expected": expected_val,
            "received": received_val,
            "output": output.strip(),
        }
