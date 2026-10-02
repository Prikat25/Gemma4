"""
Automated unit tests verifying Kaggle Google ADK compliance and packaging for all experiments in gemma4-agent.
"""

import sys
import unittest
import zipfile
from pathlib import Path

AGENT_ROOT = Path(__file__).resolve().parent.parent
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from package_submission import validate_adk_bundle, package_submission, REQUIRED_MODEL, OFFICIAL_HARNESS_TOOLS  # noqa: E402


class TestKaggleADKCompliance(unittest.TestCase):
    def test_agent_yaml_is_adk_compliant(self):
        report = validate_adk_bundle(AGENT_ROOT)
        self.assertTrue(report["valid"], f"Validation errors: {report['errors']}")
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["config"]["name"], "gemma4_swe_agent")
        self.assertEqual(report["config"]["version"], "0.1.0")
        self.assertEqual(report["config"]["model"], REQUIRED_MODEL)

    def test_official_tools_only(self):
        report = validate_adk_bundle(AGENT_ROOT)
        declared_tools = set(report["config"].get("tools", []))
        self.assertTrue(declared_tools.issubset(OFFICIAL_HARNESS_TOOLS))

    def test_experiments_e0_through_e5_valid(self):
        for exp in ["E0", "E1", "E2", "E3", "E4", "E5"]:
            exp_dir = AGENT_ROOT / "experiments" / exp
            self.assertTrue(exp_dir.exists(), f"Experiment directory {exp_dir} missing")
            report = validate_adk_bundle(exp_dir)
            self.assertTrue(report["valid"], f"Experiment {exp} validation failed: {report['errors']}")
            self.assertEqual(report["config"]["model"], REQUIRED_MODEL)

    def test_e6_lora_strictly_disabled_until_real_adapter_exists(self):
        e6_dir = AGENT_ROOT / "experiments" / "E6"
        report = validate_adk_bundle(e6_dir)
        self.assertTrue(report["valid"])
        self.assertIsNone(report["config"].get("adapter"))

    def test_submission_packaging_places_agent_yaml_at_root(self):
        out_zip = AGENT_ROOT / "harness" / "test_submission.zip"
        if out_zip.exists():
            out_zip.unlink()

        res = package_submission(AGENT_ROOT, out_zip)
        self.assertTrue(res["success"])
        self.assertTrue(out_zip.exists())

        with zipfile.ZipFile(out_zip, "r") as zf:
            namelist = zf.namelist()
            # CRITICAL KAGGLE REQUIREMENT: agent.yaml MUST BE AT ROOT
            self.assertIn("agent.yaml", namelist)
            self.assertIn("prompts/system.md", namelist)
            self.assertIn("skills/swe_reasoning/SKILL.md", namelist)
            self.assertIn("skills/bug_patterns/resources/patterns.json", namelist)
            for name in namelist:
                self.assertNotIn("..", name)

        out_zip.unlink()

    def test_mock_harness_sandbox_tools(self):
        from harness.mock_harness import SandboxHarness

        sample_repo = AGENT_ROOT / "sample_repo"
        harness = SandboxHarness(sample_repo)
        read_res = harness.read_file("pricing.py", 1, 10)
        self.assertIn("content", read_res)

        search_res = harness.search_similar_code("discount coupon")
        self.assertIsInstance(search_res, list)

        neighbor_res = harness.get_code_neighbors("calculate_price")
        self.assertIn("apply_discount", neighbor_res["callees"])

        cmd_res = harness.run_command("python3 -c 'print(42)'")
        self.assertTrue(cmd_res["success"])
        self.assertIn("42", cmd_res["stdout"])


if __name__ == "__main__":
    unittest.main()
