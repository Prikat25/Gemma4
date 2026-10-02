"""
Mock Competition Sandbox Environment emulating Kaggle swegemma / adk-submission tools.

Exposes the exact 9 official tools provided to Gemma 4:
  - run_command
  - read_file
  - edit_file
  - write_file
  - get_status
  - submit_patch
  - search_similar_code
  - get_code_neighbors
  - get_code_subgraph
"""

import os
import subprocess
import difflib
from pathlib import Path
from typing import Dict, Any, List, Optional


class SandboxHarness:
    """Emulates the offline Kaggle competition sandbox environment."""

    def __init__(self, repo_dir: Path):
        self.repo_dir = Path(repo_dir).resolve()
        self.patch_submitted = False
        self.submitted_diff: Optional[str] = None
        self.tool_call_count = 0
        self.initial_snapshots: Dict[str, str] = {}
        self._snapshot_repository()

    def _snapshot_repository(self) -> None:
        for py_file in self.repo_dir.rglob("*.py"):
            if "__pycache__" not in py_file.parts:
                rel = str(py_file.relative_to(self.repo_dir))
                self.initial_snapshots[rel] = py_file.read_text(encoding="utf-8")

    # --- Tool 1: run_command ---
    def run_command(self, command: str) -> Dict[str, Any]:
        self.tool_call_count += 1
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(self.repo_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "success": proc.returncode == 0,
        }

    # --- Tool 2: read_file ---
    def read_file(self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> Dict[str, Any]:
        self.tool_call_count += 1
        file_path = self.repo_dir / path
        if not file_path.exists():
            return {"error": f"File '{path}' does not exist"}

        lines = file_path.read_text(encoding="utf-8").splitlines()
        start = max(1, start_line or 1)
        end = min(len(lines), end_line or len(lines))
        content = "\n".join(f"{i}: {line}" for i, line in enumerate(lines[start - 1 : end], start=start))
        return {
            "path": path,
            "total_lines": len(lines),
            "start_line": start,
            "end_line": end,
            "content": content,
        }

    # --- Tool 3: edit_file ---
    def edit_file(self, path: str, search_block: str, replace_block: str) -> Dict[str, Any]:
        self.tool_call_count += 1
        file_path = self.repo_dir / path
        if not file_path.exists():
            return {"error": f"File '{path}' does not exist"}

        original = file_path.read_text(encoding="utf-8")
        if search_block not in original:
            return {"error": f"search_block not found in '{path}'"}

        updated = original.replace(search_block, replace_block, 1)
        file_path.write_text(updated, encoding="utf-8")
        return {"success": True, "path": path, "message": "File edited successfully"}

    # --- Tool 4: write_file ---
    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        self.tool_call_count += 1
        file_path = self.repo_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return {"success": True, "path": path, "message": "File written successfully"}

    # --- Tool 5: get_status ---
    def get_status(self) -> Dict[str, Any]:
        self.tool_call_count += 1
        modified_files = []
        for rel, original in self.initial_snapshots.items():
            curr_path = self.repo_dir / rel
            if curr_path.exists() and curr_path.read_text(encoding="utf-8") != original:
                modified_files.append(rel)

        return {
            "modified_files": modified_files,
            "patch_submitted": self.patch_submitted,
            "tool_calls": self.tool_call_count,
        }

    # --- Tool 6: submit_patch ---
    def submit_patch(self) -> Dict[str, Any]:
        self.tool_call_count += 1
        diff_chunks = []
        for rel, original in self.initial_snapshots.items():
            curr_path = self.repo_dir / rel
            if curr_path.exists():
                after = curr_path.read_text(encoding="utf-8")
                if after != original:
                    diff = difflib.unified_diff(
                        original.splitlines(keepends=True),
                        after.splitlines(keepends=True),
                        fromfile=f"a/{rel}",
                        tofile=f"b/{rel}",
                    )
                    diff_chunks.append("".join(diff))

        full_diff = "\n".join(diff_chunks)
        self.patch_submitted = True
        self.submitted_diff = full_diff
        return {
            "success": True,
            "patch_submitted": True,
            "diff_length": len(full_diff),
            "diff": full_diff,
        }

    # --- Tool 7: search_similar_code ---
    def search_similar_code(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        self.tool_call_count += 1
        results = []
        q_tokens = set(query.lower().split())
        for rel in self.initial_snapshots.keys():
            content = (self.repo_dir / rel).read_text(encoding="utf-8")
            matches = [line.strip() for line in content.splitlines() if any(tok in line.lower() for tok in q_tokens)]
            if matches:
                results.append({"file": rel, "matched_lines": matches[:3], "score": len(matches)})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    # --- Tool 8: get_code_neighbors ---
    def get_code_neighbors(self, symbol: str) -> Dict[str, Any]:
        self.tool_call_count += 1
        neighbors = {
            "checkout": ["validate_cart", "calculate_price", "process_payment", "send_confirmation"],
            "calculate_price": ["calculate_subtotal", "apply_discount"],
            "apply_discount": ["validate_coupon"],
            "calculate_subtotal": [],
            "validate_cart": [],
            "process_payment": [],
        }
        return {
            "symbol": symbol,
            "callees": neighbors.get(symbol, []),
            "called_by": [k for k, v in neighbors.items() if symbol in v],
        }

    # --- Tool 9: get_code_subgraph ---
    def get_code_subgraph(self, symbol: str, depth: int = 2) -> Dict[str, Any]:
        self.tool_call_count += 1
        return {
            "root_symbol": symbol,
            "depth": depth,
            "subgraph_nodes": ["checkout", "calculate_price", "apply_discount", "calculate_subtotal", "process_payment"],
            "subgraph_edges": [
                {"from": "checkout", "to": "calculate_price"},
                {"from": "calculate_price", "to": "calculate_subtotal"},
                {"from": "calculate_price", "to": "apply_discount"},
                {"from": "checkout", "to": "process_payment"},
            ],
        }
