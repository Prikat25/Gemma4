#!/usr/bin/env python3
"""
Kaggle Gemma 4 Developer Agent Submission Packager & ADK Validator.

Converts declarative ADK configurations into the exact `submission.zip` archive
expected by the competition harness:
  - `agent.yaml` at the root of `submission.zip`
  - Top-level `model: gemma-4-31b-it-qat-w4a16-ct`
  - Harness tools only (run_command, read_file, edit_file, write_file, get_status, submit_patch,
    get_code_neighbors, search_similar_code, get_code_subgraph)
  - Referenced prompts, sub-agents, and skills included
  - No `../` path traversal
  - Real LoRA verification (requires adapter_config.json and adapter_model.safetensors if adapter is set)
"""

import os
import sys
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional

WORKSPACE_ROOT = Path(__file__).resolve().parent

OFFICIAL_HARNESS_TOOLS = {
    "run_command",
    "read_file",
    "edit_file",
    "write_file",
    "get_status",
    "submit_patch",
    "get_code_neighbors",
    "search_similar_code",
    "get_code_subgraph",
}

REQUIRED_MODEL = "gemma-4-31b-it-qat-w4a16-ct"


def parse_simple_yaml(text: str) -> Dict[str, Any]:
    """Zero-dependency YAML parser for ADK configuration validation."""
    data: Dict[str, Any] = {}
    current_key = None
    in_list = False

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if line.startswith("  - ") and current_key:
            val = stripped[2:].strip().strip('"').strip("'")
            if not isinstance(data.get(current_key), list):
                data[current_key] = []
            data[current_key].append(val)
            continue

        if ":" in stripped:
            parts = stripped.split(":", 1)
            key = parts[0].strip()
            val = parts[1].strip()

            if val == "" or val.startswith("#"):
                current_key = key
                data[key] = [] if line.startswith(" ") else {}
            else:
                val = val.split(" #")[0].strip().strip('"').strip("'")
                if val.lower() == "null" or val == "~":
                    val = None
                elif val.lower() == "true":
                    val = True
                elif val.lower() == "false":
                    val = False
                elif val.isdigit():
                    val = int(val)
                data[key] = val
                current_key = key

    return data


def validate_adk_bundle(bundle_dir: Path) -> Dict[str, Any]:
    yaml_file = bundle_dir / "agent.yaml"
    if not yaml_file.exists():
        return {
            "valid": False,
            "errors": [f"Missing required agent.yaml in {bundle_dir}"],
            "warnings": [],
        }

    raw_yaml = yaml_file.read_text(encoding="utf-8")
    cfg = parse_simple_yaml(raw_yaml)
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Top-level name & model
    if not cfg.get("name"):
        errors.append("agent.yaml missing 'name'")

    model = cfg.get("model")
    if model != REQUIRED_MODEL:
        errors.append(f"Top-level 'model' must be '{REQUIRED_MODEL}', found '{model}'")

    # 2. Check for unsafe path traversal
    for match_line in raw_yaml.splitlines():
        if ".." in match_line:
            errors.append(f"Forbidden path traversal '..' detected: {match_line.strip()}")

    # 3. Instruction file existence
    instruction = cfg.get("instruction")
    if instruction:
        inst_path = bundle_dir / instruction
        if not inst_path.exists() and not (WORKSPACE_ROOT / instruction).exists():
            errors.append(f"Instruction file '{instruction}' not found")

    # 4. Official tools validation
    tools = cfg.get("tools", [])
    if isinstance(tools, list):
        for t in tools:
            if t not in OFFICIAL_HARNESS_TOOLS:
                errors.append(f"Tool '{t}' is not an official Kaggle competition harness tool")

    # 5. Skills verification
    skills = cfg.get("skills", [])
    if isinstance(skills, list):
        for sk in skills:
            sk_dir = bundle_dir / "skills" / sk
            if not sk_dir.exists():
                sk_dir = WORKSPACE_ROOT / "skills" / sk
            if not sk_dir.exists():
                errors.append(f"Skill directory not found for declared skill '{sk}'")
            else:
                skill_md = sk_dir / "SKILL.md"
                if not skill_md.exists():
                    errors.append(f"Missing SKILL.md in skill '{sk}'")
                elif "name:" not in skill_md.read_text(encoding="utf-8"):
                    warnings.append(f"SKILL.md in '{sk}' missing YAML frontmatter 'name:'")

    # 6. Subagent (agent_tools) verification
    agent_tools = cfg.get("agent_tools", [])
    if isinstance(agent_tools, list):
        for at in agent_tools:
            # Check sub_agents directory
            sa_dir = bundle_dir / "sub_agents"
            if not sa_dir.exists():
                sa_dir = WORKSPACE_ROOT / "sub_agents"
            if not sa_dir.exists():
                warnings.append("Declared agent_tools but sub_agents directory not found")

    # 7. LoRA adapter verification
    adapter = cfg.get("adapter")
    if adapter:
        adapter_path = bundle_dir / adapter
        if not adapter_path.exists():
            adapter_path = WORKSPACE_ROOT / adapter
        if not adapter_path.exists():
            errors.append(f"LoRA adapter '{adapter}' declared but directory not found. Fake verification prohibited.")
        else:
            cfg_json = adapter_path / "adapter_config.json"
            weights = adapter_path / "adapter_model.safetensors"
            if not cfg_json.exists() or not weights.exists():
                errors.append(f"LoRA directory '{adapter}' missing adapter_config.json or adapter_model.safetensors")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "config": cfg,
    }


def package_submission(bundle_dir: Path, output_zip: Path) -> Dict[str, Any]:
    validation = validate_adk_bundle(bundle_dir)
    if not validation["valid"]:
        raise ValueError(f"ADK validation failed: {validation['errors']}")

    output_zip = Path(output_zip).resolve()
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    files_added: List[str] = []

    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. agent.yaml MUST BE AT ARCHIVE ROOT
        root_agent_yaml = bundle_dir / "agent.yaml"
        zf.write(root_agent_yaml, arcname="agent.yaml")
        files_added.append("agent.yaml")

        # 2. Add local directories in bundle_dir if present
        for sub in ["prompts", "skills", "sub_agents", "configs", "adapters"]:
            local_sub = bundle_dir / sub
            shared_sub = WORKSPACE_ROOT / sub
            source_dir = local_sub if local_sub.exists() else (shared_sub if shared_sub.exists() else None)

            if source_dir and source_dir.is_dir():
                for p in sorted(source_dir.rglob("*")):
                    if p.is_file() and "__pycache__" not in p.parts and not p.name.startswith("."):
                        arc_name = str(p.relative_to(source_dir.parent))
                        if arc_name not in files_added:
                            zf.write(p, arcname=arc_name)
                            files_added.append(arc_name)

    return {
        "success": True,
        "output_path": str(output_zip),
        "archive_size_bytes": output_zip.stat().st_size,
        "files_count": len(files_added),
        "agent_yaml_at_root": "agent.yaml" in files_added,
        "model": REQUIRED_MODEL,
        "validation": validation,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Package ADK submission for Kaggle Gemma 4 Developer Agent competition")
    parser.add_argument("--experiment", type=str, default=None, help="Experiment folder (e.g. E0, E1, E2, E3, E4, E5, E6). Defaults to root agent.yaml.")
    parser.add_argument("--output", type=str, default="submission.zip", help="Output path for submission.zip")
    parser.add_argument("--validate-only", action="store_true", help="Run ADK validation only without building zip")
    args = parser.parse_args()

    if args.experiment:
        target_dir = WORKSPACE_ROOT / "experiments" / args.experiment.upper()
        if not target_dir.exists():
            target_dir = WORKSPACE_ROOT / "experiments" / args.experiment
    else:
        target_dir = WORKSPACE_ROOT

    if args.validate_only:
        report = validate_adk_bundle(target_dir)
        print("ADK Validation:", "PASSED" if report["valid"] else "FAILED")
        if report["errors"]:
            print("Errors:")
            for err in report["errors"]:
                print(f"  - {err}")
        if report["warnings"]:
            print("Warnings:")
            for w in report["warnings"]:
                print(f"  - {w}")
        sys.exit(0 if report["valid"] else 1)

    out_zip = Path(args.output)
    if not out_zip.is_absolute():
        out_zip = WORKSPACE_ROOT / out_zip

    res = package_submission(target_dir, out_zip)
    print(f"Packaging SUCCESS:")
    print(f"  Target: {res['output_path']} ({res['archive_size_bytes']} bytes)")
    print(f"  Files: {res['files_count']} files packaged")
    print(f"  agent.yaml at root: {res['agent_yaml_at_root']}")
    print(f"  Model: {res['model']}")


if __name__ == "__main__":
    main()
