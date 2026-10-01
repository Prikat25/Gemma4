"""Automated backend contract & pipeline verification suite for Gemma 4 SWE Agent."""

import json
import sys
import unittest
from pathlib import Path

AGENT_ROOT = Path(__file__).resolve().parent.parent
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from core.pipeline import Gemma4AgentPipeline, DEFAULT_ISSUE  # noqa: E402
from core.schemas import ContractViolationError  # noqa: E402
from core.config_loader import load_experiment_config  # noqa: E402
from tools.repo_tools import RepositoryAnalyzer  # noqa: E402


class TestGemma4AgentBackend(unittest.TestCase):
    def test_e5_full_pipeline_passes_and_generates_knowledge_artifacts(self):
        pipeline = Gemma4AgentPipeline(agent_root=AGENT_ROOT, experiment="E5")
        res = pipeline.run_task(issue_text=DEFAULT_ISSUE)

        self.assertTrue(res["passed"])
        self.assertIn("pricing.py", res["patch"])
        self.assertIn("discount_amount = apply_discount(subtotal, discount)", res["patch"])

        flows = res["repository_knowledge_summary"]["execution_flows"]
        self.assertIn("checkout", flows)
        expected_chain = [
            "checkout",
            "validate_cart",
            "calculate_price",
            "calculate_subtotal",
            "apply_discount",
            "validate_coupon",
            "process_payment",
            "send_confirmation",
        ]
        self.assertEqual(flows["checkout"], expected_chain)

        kdir = AGENT_ROOT / "repository_knowledge"
        for artifact in [
            "repo_summary.md",
            "functions.json",
            "classes.json",
            "modules.json",
            "tests.json",
            "call_graph.json",
            "flow_graph.json",
            "execution_flows.md",
            "logger_state.json",
        ]:
            self.assertTrue((kdir / artifact).exists(), f"Missing artifact: {artifact}")

    def test_planner_is_strictly_forbidden_from_editing_code(self):
        cfg = load_experiment_config(AGENT_ROOT, "E5")
        analyzer = RepositoryAnalyzer(
            repo_path=AGENT_ROOT / "sample_repo",
            knowledge_dir=AGENT_ROOT / "repository_knowledge",
            config=cfg,
        )
        with self.assertRaises(ContractViolationError):
            analyzer.safe_edit(
                caller_role="planner",
                rel_file="pricing.py",
                search_block="subtotal",
                replace_block="subtotal",
                files_modified_so_far=[],
            )

    def test_failure_analyzer_iterative_repair_loop(self):
        pipeline = Gemma4AgentPipeline(agent_root=AGENT_ROOT, experiment="E5")
        res = pipeline.run_task(
            issue_text=DEFAULT_ISSUE,
            demonstrate_failure_recovery=True,
        )
        self.assertTrue(res["passed"])
        self.assertEqual(res["iterations_executed"], 2)
        self.assertEqual(len(res["failure_analyses"]), 1)
        self.assertEqual(
            res["failure_analyses"][0]["failure_type"],
            "incorrect_discount_application",
        )
        self.assertEqual(
            res["failure_analyses"][0]["likely_function"],
            "calculate_price",
        )

    def test_e0_to_e6_experiment_configs_and_toggles(self):
        for exp_id in ["E0", "E1", "E2", "E3", "E4", "E5", "E6"]:
            cfg = load_experiment_config(AGENT_ROOT, exp_id)
            self.assertEqual(cfg["experiment_id"], exp_id)
            self.assertEqual(cfg["model"]["name"], "gemma-4-31b-it-qat-w4a16-ct")

        p0 = Gemma4AgentPipeline(agent_root=AGENT_ROOT, experiment="E0")
        r0 = p0.run_task()
        self.assertEqual(r0["repository_knowledge_summary"]["execution_flows"], {})
        self.assertEqual(r0["bug_db_matches"], [])

        p6 = Gemma4AgentPipeline(agent_root=AGENT_ROOT, experiment="E6")
        r6 = p6.run_task()
        self.assertTrue(r6["model_info"]["lora_status"]["lora_enabled"])
        self.assertEqual(
            r6["model_info"]["lora_status"]["duplicate_decoder_layer_check"],
            "PASSED_SINGLE_REGISTRATION",
        )


if __name__ == "__main__":
    unittest.main()
