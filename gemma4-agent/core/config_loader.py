"""Configuration loader supporting config/experiment.yaml and E0-E6 presets."""

from pathlib import Path
from typing import Dict, Any, Union, List, Optional


def _parse_scalar(val: str) -> Any:
    val = val.strip()
    if val == "" or val.lower() in ("null", "none", "~"):
        return None
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    if (val.startswith('"') and val.endswith('"')) or (
        val.startswith("'") and val.endswith("'")
    ):
        return val[1:-1]
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        return val


def _simple_yaml_load(text: str) -> Dict[str, Any]:
    """Zero-dependency indentation-aware YAML subset parser for experiment configs."""
    root: Dict[str, Any] = {}
    stack: List[tuple[int, Union[Dict[str, Any], List[Any]]]] = [(-1, root)]

    lines = text.splitlines()
    for idx, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if " #" in raw_line and not ('"' in raw_line or "'" in raw_line):
            raw_line = raw_line.split(" #", 1)[0]
            stripped = raw_line.strip()

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()

        parent = stack[-1][1]

        if stripped.startswith("- "):
            item_val = _parse_scalar(stripped[2:])
            if isinstance(parent, list):
                parent.append(item_val)
            continue

        if ":" in stripped:
            key, rest = stripped.split(":", 1)
            key = key.strip()
            rest = rest.strip()
            if rest == "":
                next_is_list = False
                for next_line in lines[idx + 1 :]:
                    ns = next_line.strip()
                    if not ns or ns.startswith("#"):
                        continue
                    if ns.startswith("- "):
                        next_is_list = True
                    break
                container: Union[Dict[str, Any], List[Any]] = [] if next_is_list else {}
                if isinstance(parent, dict):
                    parent[key] = container
                stack.append((indent, container))
            else:
                if isinstance(parent, dict):
                    parent[key] = _parse_scalar(rest)
    return root


def load_yaml_file(path: Union[str, Path]) -> Dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    raw_text = file_path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(raw_text)
        if isinstance(loaded, dict):
            return loaded
    except Exception:
        pass
    return _simple_yaml_load(raw_text)


EXPERIMENT_PRESET_MAP: Dict[str, str] = {
    "E0": "experiments/baseline.yaml",
    "baseline": "experiments/baseline.yaml",
    "E1": "experiments/summaries.yaml",
    "summaries": "experiments/summaries.yaml",
    "E2": "experiments/flow_graph.yaml",
    "flow_graph": "experiments/flow_graph.yaml",
    "E3": "experiments/e3_bug_db.yaml",
    "bug_db": "experiments/e3_bug_db.yaml",
    "E4": "experiments/e4_planner.yaml",
    "planner": "experiments/e4_planner.yaml",
    "E5": "experiments/e5_failure_loop.yaml",
    "failure_loop": "experiments/e5_failure_loop.yaml",
    "E6": "experiments/lora.yaml",
    "lora": "experiments/lora.yaml",
}


def load_experiment_config(
    agent_root: Union[str, Path],
    experiment_or_path: Optional[str] = None,
) -> Dict[str, Any]:
    root = Path(agent_root)
    if not experiment_or_path:
        target = root / "config" / "experiment.yaml"
    elif experiment_or_path in EXPERIMENT_PRESET_MAP:
        target = root / EXPERIMENT_PRESET_MAP[experiment_or_path]
    else:
        candidate = Path(experiment_or_path)
        target = candidate if candidate.is_absolute() else root / candidate
    config = load_yaml_file(target)
    config["_config_path"] = str(target)
    return config
