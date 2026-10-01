#!/usr/bin/env python3
"""
Kaggle Gemma 4 Developer Agent Submission Packager & Validator.

Builds a valid `submission.zip` according to Google ADK & Kaggle competition specs:
- `agent.yaml` placed at the root of `submission.zip`
- Model alias declared as `gemma-4-31b-it-qat-w4a16-ct`
- Includes prompts/, skills/, tools/, core/, config/, knowledge/
- Validates prompt references and tool declarations
"""

import sys
import zipfile
from pathlib import Path
from typing import Dict, Any, List

AGENT_ROOT = Path(__file__).resolve().parent
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from core.config_loader import load_yaml_file  # noqa: E402

KAGGLE_REQUIRED_MODEL = "gemma-4-31b-it-qat-w4a16-ct"
KAGGLE_HARNESS_TOOLS = {
    "run_command",
    "read_file",
    "edit_file",
    "write_file",
    "submit_patch",
    "get_status",
    "search_similar_code",
    "get_code_neighbors",
    "get_code_subgraph",
}


def validate_agent_config(agent_root: Path) -> Dict[str, Any]:
    yaml_path = agent_root / "agent.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"agent.yaml not found at: {yaml_path}")

    cfg = load_yaml_file(yaml_path)
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Check top-level name and version
    name = cfg.get("name")
    if not name:
        errors.append("Missing required 'name' field in agent.yaml")

    # 2. Check top-level model declaration
    model = cfg.get("model")
    if not model:
        errors.append(f"Missing required top-level 'model' field in agent.yaml (must be '{KAGGLE_REQUIRED_MODEL}')")
    elif model != KAGGLE_REQUIRED_MODEL:
        errors.append(f"Invalid model '{model}': Kaggle competition strictly requires '{KAGGLE_REQUIRED_MODEL}'")

    # 3. Check model_config declaration
    model_cfg = cfg.get("model_config", {})
    if not isinstance(model_cfg, dict):
        errors.append("'model_config' must be a dictionary")
    else:
        base_model = model_cfg.get("base_model")
        if base_model != KAGGLE_REQUIRED_MODEL:
            errors.append(f"model_config.base_model must be '{KAGGLE_REQUIRED_MODEL}'")

    # 4. Check prompt file existence
    instruction_path = cfg.get("instruction") or cfg.get("prompt")
    if instruction_path and not (agent_root / instruction_path).exists():
        errors.append(f"Referenced instruction file does not exist: {instruction_path}")

    subagents = cfg.get("subagents", {})
    for sa_name, sa_info in subagents.items():
        if isinstance(sa_info, dict):
            sa_prompt = sa_info.get("prompt")
            if sa_prompt and not (agent_root / sa_prompt).exists():
                warnings.append(f"Subagent '{sa_name}' prompt file not found: {sa_prompt}")

    # 5. Check declared tools against Kaggle harness tools
    tools = cfg.get("tools", [])
    for t in tools:
        if t not in KAGGLE_HARNESS_TOOLS:
            warnings.append(f"Tool '{t}' is a custom tool; ensure custom agent_tool runner is provided if not in standard sandbox.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "config": {
            "name": name,
            "version": cfg.get("version"),
            "model": model,
            "model_config": model_cfg,
            "tools_count": len(tools),
            "subagents_count": len(subagents),
        },
    }


def build_submission_zip(agent_root: Path, output_zip_path: Path) -> Dict[str, Any]:
    validation = validate_agent_config(agent_root)
    if not validation["valid"]:
        raise ValueError(f"Cannot build submission: validation failed with errors: {validation['errors']}")

    output_zip_path = Path(output_zip_path).resolve()
    output_zip_path.parent.mkdir(parents=True, exist_ok=True)

    included_directories = [
        "config",
        "experiments",
        "prompts",
        "skills",
        "tools",
        "core",
        "knowledge",
        "adapters",
    ]
    included_root_files = [
        "agent.yaml",
        "cli.py",
        "GEMMA4_AGENT_MANIFEST.md",
    ]

    files_added: List[str] = []

    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Add agent.yaml and key root files directly at root of ZIP
        for rf in included_root_files:
            file_path = agent_root / rf
            if file_path.exists():
                zf.write(file_path, arcname=rf)
                files_added.append(rf)

        # 2. Add directories recursively
        for d in included_directories:
            dir_path = agent_root / d
            if dir_path.exists() and dir_path.is_dir():
                for p in sorted(dir_path.rglob("*")):
                    if p.is_file() and "__pycache__" not in p.parts and not p.name.startswith("."):
                        arc_name = str(p.relative_to(agent_root))
                        zf.write(p, arcname=arc_name)
                        files_added.append(arc_name)

    zip_size_bytes = output_zip_path.stat().st_size

    return {
        "success": True,
        "archive_path": str(output_zip_path),
        "archive_size_bytes": zip_size_bytes,
        "files_count": len(files_added),
        "files_added": files_added,
        "agent_yaml_at_root": "agent.yaml" in files_added,
        "model_validated": KAGGLE_REQUIRED_MODEL,
        "validation_report": validation,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Package submission.zip for Kaggle Gemma 4 Developer Agent competition")
    parser.add_argument("--output", type=str, default="submission.zip", help="Path to output submission.zip")
    parser.add_argument("--validate-only", action="store_true", help="Only validate agent.yaml without creating zip")
    args = parser.parse_args()

    if args.validate_only:
        report = validate_agent_config(AGENT_ROOT)
        print(f"Validation: {'PASSED' if report['valid'] else 'FAILED'}")
        if report["errors"]:
            print("Errors:", report["errors"])
        if report["warnings"]:
            print("Warnings:", report["warnings"])
        sys.exit(0 if report["valid"] else 1)

    out_zip = Path(args.output)
    if not out_zip.is_absolute():
        out_zip = AGENT_ROOT / out_zip

    res = build_submission_zip(AGENT_ROOT, out_zip)
    print(f"Successfully packaged {res['files_count']} files into {res['archive_path']} ({res['archive_size_bytes']} bytes)")
    print(f"agent.yaml at root: {res['agent_yaml_at_root']}")
    print(f"Target Model: {res['model_validated']}")


if __name__ == "__main__":
    main()
