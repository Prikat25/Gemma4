"""Two-layer graph builder: Structural Call Graph + Behavioral Execution Flow Graph."""

import json
from pathlib import Path
from typing import Dict, List, Any, Set


class FlowGraphBuilder:
    def __init__(self, knowledge_dir: Path):
        self.knowledge_dir = Path(knowledge_dir).resolve()

    def build_graphs(self, repo_knowledge: Dict[str, Any]) -> Dict[str, Any]:
        functions: List[Dict[str, Any]] = repo_knowledge.get("functions", [])
        func_by_name: Dict[str, Dict[str, Any]] = {
            f["function"]: f for f in functions
        }

        call_graph: Dict[str, List[str]] = {}
        for fn in functions:
            name = fn["function"]
            internal_calls = [c for c in fn.get("calls", []) if c in func_by_name]
            call_graph[name] = internal_calls

        entry_points = [
            fn["function"]
            for fn in functions
            if not fn.get("called_by") and fn.get("calls")
        ]
        if not entry_points and functions:
            entry_points = [functions[0]["function"]]

        flows: Dict[str, List[str]] = {}
        hierarchical_trees: Dict[str, List[Dict[str, Any]]] = {}
        divergences: List[Dict[str, Any]] = []

        for entry in entry_points:
            visited: Set[str] = set()
            ordered_chain: List[str] = []
            tree_steps: List[Dict[str, Any]] = []
            self._dfs_flow(
                current=entry,
                depth=0,
                func_by_name=func_by_name,
                call_graph=call_graph,
                visited=visited,
                ordered_chain=ordered_chain,
                tree_steps=tree_steps,
                divergences=divergences,
            )
            flows[entry] = ordered_chain
            hierarchical_trees[entry] = tree_steps

        flow_graph_payload = {
            "entry_points": entry_points,
            "direct_call_map": call_graph,
            "execution_flows": flows,
            "flow_trees": hierarchical_trees,
            "detected_flow_anomalies": divergences,
        }

        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        (self.knowledge_dir / "call_graph.json").write_text(
            json.dumps(call_graph, indent=2), encoding="utf-8"
        )
        (self.knowledge_dir / "flow_graph.json").write_text(
            json.dumps(flow_graph_payload, indent=2), encoding="utf-8"
        )
        (self.knowledge_dir / "execution_flows.md").write_text(
            self._render_execution_flows_md(flow_graph_payload), encoding="utf-8"
        )

        return flow_graph_payload

    def _dfs_flow(
        self,
        current: str,
        depth: int,
        func_by_name: Dict[str, Dict[str, Any]],
        call_graph: Dict[str, List[str]],
        visited: Set[str],
        ordered_chain: List[str],
        tree_steps: List[Dict[str, Any]],
        divergences: List[Dict[str, Any]],
    ) -> None:
        if current in visited:
            return
        visited.add(current)
        ordered_chain.append(current)

        fn_meta = func_by_name.get(current, {})
        logic_lines = fn_meta.get("important_logic", [])
        for step in logic_lines:
            if "RETURN VALUE IGNORED" in step:
                divergences.append(
                    {
                        "function": current,
                        "file": fn_meta.get("file", ""),
                        "anomaly": step,
                        "severity": "high",
                        "explanation": (
                            f"In `{current}()`, a downstream function in the execution flow is invoked "
                            "as a bare statement without capturing or returning its result."
                        ),
                    }
                )

        tree_steps.append(
            {
                "function": current,
                "file": fn_meta.get("file", ""),
                "depth": depth,
                "callees": call_graph.get(current, []),
                "important_logic": logic_lines,
            }
        )

        for callee in call_graph.get(current, []):
            self._dfs_flow(
                current=callee,
                depth=depth + 1,
                func_by_name=func_by_name,
                call_graph=call_graph,
                visited=visited,
                ordered_chain=ordered_chain,
                tree_steps=tree_steps,
                divergences=divergences,
            )

    def _render_execution_flows_md(self, payload: Dict[str, Any]) -> str:
        lines = [
            "# Behavioral Execution Flows",
            "",
            "Generated during `UNDERSTAND` phase for repository memory.",
            "",
        ]
        for entry, steps in payload.get("flow_trees", {}).items():
            lines.append(f"## Entry Point: `{entry}()`")
            lines.append("```text")
            lines.append("REQUEST")
            for step in steps:
                indent = "  " * step["depth"]
                lines.append(f"{indent}  ↓")
                lines.append(f"{indent}{step['function']}()  [{step['file']}]")
            lines.append("```")
            lines.append("")

        anomalies = payload.get("detected_flow_anomalies", [])
        if anomalies:
            lines.append("## Detected Flow Divergences / Anomalies")
            for anom in anomalies:
                lines.append(
                    f"- **`{anom['file']}::{anom['function']}`**: {anom['anomaly']} — {anom['explanation']}"
                )
        return "\n".join(lines) + "\n"
