#!/usr/bin/env python3
"""
CLI Runner for the Gemma 4 SWE Agent Backend.

Usage examples:
  python3 cli.py --experiment E5
  python3 cli.py --experiment E5 --demo-failure-loop
  python3 cli.py --matrix
"""

import argparse
import json
import sys
from pathlib import Path

AGENT_ROOT = Path(__file__).resolve().parent
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from core.pipeline import Gemma4AgentPipeline, DEFAULT_ISSUE  # noqa: E402


def run_ablation_matrix() -> dict:
    experiments = ["E0", "E1", "E2", "E3", "E4", "E5", "E6"]
    matrix_results = []
    for exp_id in experiments:
        pipeline = Gemma4AgentPipeline(
            agent_root=AGENT_ROOT,
            experiment=exp_id,
        )
        demo_recovery = exp_id in ("E5", "E6")
        result = pipeline.run_task(
            issue_text=DEFAULT_ISSUE,
            demonstrate_failure_recovery=demo_recovery,
        )
        arch = pipeline.config.get("architecture", {})
        train = pipeline.config.get("training", {})
        matrix_results.append(
            {
                "experiment": exp_id,
                "repo_summaries": bool(arch.get("use_function_summarizer", False)),
                "flow_graph": bool(arch.get("use_flow_graph", False)),
                "bug_db": bool(arch.get("use_bug_lookup", False)),
                "planner": bool(arch.get("use_planner", False)),
                "failure_loop": bool(arch.get("use_failure_analyzer", False)),
                "lora": bool(train.get("use_lora", False)),
                "passed": result["passed"],
                "iterations_executed": result["iterations_executed"],
                "flow_anomalies_detected": len(
                    result["repository_knowledge_summary"]["detected_flow_anomalies"]
                ),
                "bug_matches_count": len(result["bug_db_matches"]),
                "complexity_score": result["complexity_estimate"]["complexity_score"],
                "allocated_minutes": result["time_budget"]["allocated_task_minutes"],
            }
        )
    return {
        "competition_model": "gemma-4-31b-it-qat-w4a16-ct",
        "total_budget_hours": 12,
        "matrix": matrix_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gemma 4 SWE Agent Backend CLI (UNDERSTAND -> LOCALIZE -> PLAN -> PATCH -> VALIDATE -> LEARN)"
    )
    parser.add_argument(
        "--experiment",
        type=str,
        default="E5",
        help="Experiment ID (E0..E6) or path to YAML config (default: E5)",
    )
    parser.add_argument(
        "--issue",
        type=str,
        default=DEFAULT_ISSUE,
        help="Issue description to solve",
    )
    parser.add_argument(
        "--demo-failure-loop",
        action="store_true",
        help="Simulate an incomplete Attempt #1 to verify FailureAnalyzer -> Planner -> Coder recovery on Attempt #2",
    )
    parser.add_argument(
        "--matrix",
        action="store_true",
        help="Run the full E0-E6 scientific experiment ablation matrix",
    )
    parser.add_argument(
        "--package-submission",
        action="store_true",
        help="Validate agent.yaml and build Kaggle submission.zip with agent.yaml at root",
    )
    parser.add_argument(
        "--validate-submission",
        action="store_true",
        help="Validate agent.yaml against Google ADK & Kaggle competition specifications",
    )
    args = parser.parse_args()

    if args.validate_submission:
        from package_submission import validate_agent_config
        report = validate_agent_config(AGENT_ROOT)
        print(json.dumps(report, indent=2))
        return

    if args.package_submission:
        from package_submission import build_submission_zip
        out_zip = AGENT_ROOT / "submission.zip"
        res = build_submission_zip(AGENT_ROOT, out_zip)
        print(json.dumps(res, indent=2))
        return

    if args.matrix:
        out = run_ablation_matrix()
        print(json.dumps(out, indent=2))
        return

    pipeline = Gemma4AgentPipeline(
        agent_root=AGENT_ROOT,
        experiment=args.experiment,
    )
    result = pipeline.run_task(
        issue_text=args.issue,
        demonstrate_failure_recovery=args.demo_failure_loop,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
