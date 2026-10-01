"""Repository AST extraction, persistent knowledge caching, safe editing, and diff review tools."""

import ast
import difflib
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from core.schemas import (
    FunctionSummary,
    ClassSummary,
    TestSummary,
    ContractViolationError,
)


def _unparse_annotation(node: Optional[ast.AST]) -> str:
    if node is None:
        return "Any"
    try:
        return ast.unparse(node)
    except Exception:
        return "Any"


def _extract_important_logic(func_node: ast.FunctionDef) -> Tuple[List[str], List[str]]:
    logic_steps: List[str] = []
    side_effects: List[str] = []

    for stmt in func_node.body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
            continue
        if isinstance(stmt, ast.Assign):
            targets = [ast.unparse(t) for t in stmt.targets]
            val_str = ast.unparse(stmt.value)
            logic_steps.append(f"{', '.join(targets)} = {val_str}")
        elif isinstance(stmt, ast.If):
            cond_str = ast.unparse(stmt.test)
            body_summaries = []
            for sub in stmt.body:
                if isinstance(sub, ast.Expr) and isinstance(sub.value, ast.Call):
                    call_str = ast.unparse(sub.value)
                    body_summaries.append(
                        f"calls {call_str} as standalone statement (RETURN VALUE IGNORED)"
                    )
                else:
                    body_summaries.append(ast.unparse(sub).splitlines()[0])
            logic_steps.append(f"if {cond_str}: {'; '.join(body_summaries)}")
        elif isinstance(stmt, ast.Return):
            ret_str = ast.unparse(stmt.value) if stmt.value else "None"
            logic_steps.append(f"returns {ret_str}")
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call_str = ast.unparse(stmt.value)
            logic_steps.append(f"executes {call_str}")

    return logic_steps, side_effects


def _extract_calls_in_order(node: ast.AST) -> List[str]:
    calls: List[str] = []
    builtins_ignore = {
        "len",
        "range",
        "int",
        "float",
        "str",
        "round",
        "min",
        "max",
        "list",
        "dict",
        "set",
        "tuple",
        "isinstance",
        "print",
        "ValueError",
        "RuntimeError",
        "Exception",
    }
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            func_name = None
            if isinstance(sub.func, ast.Name):
                func_name = sub.func.id
            elif isinstance(sub.func, ast.Attribute):
                func_name = sub.func.attr
            if func_name and func_name not in builtins_ignore and func_name not in calls:
                calls.append(func_name)
    return calls


class RepositoryAnalyzer:
    def __init__(self, repo_path: Path, knowledge_dir: Path, config: Dict[str, Any]):
        self.repo_path = Path(repo_path).resolve()
        self.knowledge_dir = Path(knowledge_dir).resolve()
        self.config = config
        self.repo_cfg = config.get("repository", {})
        self.arch_cfg = config.get("architecture", {})
        self._cache: Optional[Dict[str, Any]] = None
        self._file_snapshots: Dict[str, str] = {}

    def snapshot_files(self) -> None:
        for py_file in sorted(self.repo_path.rglob("*.py")):
            if "__pycache__" in py_file.parts or ".git" in py_file.parts:
                continue
            rel = str(py_file.relative_to(self.repo_path))
            if rel not in self._file_snapshots:
                self._file_snapshots[rel] = py_file.read_text(encoding="utf-8")

    def restore_snapshots(self) -> None:
        for rel, content in self._file_snapshots.items():
            (self.repo_path / rel).write_text(content, encoding="utf-8")

    def scan_and_summarize(self, force_refresh: bool = False) -> Dict[str, Any]:
        if (
            self._cache is not None
            and not force_refresh
            and self.repo_cfg.get("persistent_cache", True)
        ):
            return self._cache

        self.snapshot_files()
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)

        functions: List[FunctionSummary] = []
        classes: List[ClassSummary] = []
        tests: List[TestSummary] = []
        modules: Dict[str, Dict[str, Any]] = {}

        for py_file in sorted(self.repo_path.rglob("*.py")):
            if "__pycache__" in py_file.parts or ".git" in py_file.parts:
                continue
            rel_path = str(py_file.relative_to(self.repo_path))
            source = py_file.read_text(encoding="utf-8")
            lines = source.splitlines()
            tree = ast.parse(source, filename=rel_path)

            imports: List[str] = []
            module_funcs: List[str] = []
            module_classes: List[str] = []

            for node in tree.body:
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    for alias in node.names:
                        imports.append(f"{mod}.{alias.name}" if mod else alias.name)
                elif isinstance(node, ast.FunctionDef):
                    module_funcs.append(node.name)
                    if rel_path.startswith("tests/") or node.name.startswith("test_"):
                        tests.append(self._parse_test_node(node, rel_path, lines))
                    else:
                        functions.append(self._parse_function_node(node, rel_path, lines))
                elif isinstance(node, ast.ClassDef):
                    module_classes.append(node.name)
                    bases = [_unparse_annotation(b) for b in node.bases]
                    methods: List[str] = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods.append(item.name)
                            if (
                                rel_path.startswith("tests/")
                                or node.name.startswith("Test")
                                or item.name.startswith("test_")
                            ):
                                if item.name.startswith("test_"):
                                    tests.append(
                                        self._parse_test_node(item, rel_path, lines)
                                    )
                            else:
                                functions.append(
                                    self._parse_function_node(item, rel_path, lines)
                                )
                    doc = ast.get_docstring(node) or f"Class {node.name} in {rel_path}"
                    classes.append(
                        ClassSummary(
                            class_name=node.name,
                            file=rel_path,
                            line_start=node.lineno,
                            line_end=getattr(node, "end_lineno", node.lineno),
                            bases=bases,
                            methods=methods,
                            purpose=doc.splitlines()[0],
                        )
                    )

            modules[rel_path] = {
                "file": rel_path,
                "imports": imports,
                "functions": module_funcs,
                "classes": module_classes,
                "line_count": len(lines),
            }

        func_map = {f.function: f for f in functions}
        for f in functions:
            for callee in f.calls:
                if callee in func_map and f.function not in func_map[callee].called_by:
                    func_map[callee].called_by.append(f.function)

        knowledge = {
            "modules": modules,
            "functions": [f.to_dict(include_source=True) for f in functions],
            "classes": [c.to_dict() for c in classes],
            "tests": [t.to_dict(include_source=True) for t in tests],
        }

        (self.knowledge_dir / "modules.json").write_text(
            json.dumps(modules, indent=2), encoding="utf-8"
        )
        (self.knowledge_dir / "functions.json").write_text(
            json.dumps([f.to_dict(include_source=False) for f in functions], indent=2),
            encoding="utf-8",
        )
        (self.knowledge_dir / "classes.json").write_text(
            json.dumps([c.to_dict() for c in classes], indent=2),
            encoding="utf-8",
        )
        (self.knowledge_dir / "tests.json").write_text(
            json.dumps([t.to_dict(include_source=False) for t in tests], indent=2),
            encoding="utf-8",
        )

        summary_md = self._build_repo_summary_md(modules, functions, classes, tests)
        (self.knowledge_dir / "repo_summary.md").write_text(summary_md, encoding="utf-8")

        self._cache = knowledge
        return knowledge

    def _parse_function_node(
        self, node: ast.FunctionDef, rel_path: str, lines: List[str]
    ) -> FunctionSummary:
        inputs = [arg.arg for arg in node.args.args if arg.arg != "self"]
        outputs = _unparse_annotation(node.returns)
        doc = ast.get_docstring(node) or f"Executes {node.name}"
        calls = _extract_calls_in_order(node)
        logic_steps, side_effects = _extract_important_logic(node)
        end_line = getattr(node, "end_lineno", node.lineno)
        source_slice = "\n".join(lines[node.lineno - 1 : end_line])

        return FunctionSummary(
            function=node.name,
            file=rel_path,
            line_start=node.lineno,
            line_end=end_line,
            inputs=inputs,
            outputs=outputs,
            purpose=doc.splitlines()[0],
            calls=calls,
            called_by=[],
            side_effects=side_effects,
            important_logic=logic_steps,
            source_code=source_slice,
        )

    def _parse_test_node(
        self, node: ast.FunctionDef, rel_path: str, lines: List[str]
    ) -> TestSummary:
        calls = _extract_calls_in_order(node)
        assertion_methods = {
            "assertEqual",
            "assertTrue",
            "assertFalse",
            "assertRaises",
            "assertIn",
            "assertIsNotNone",
        }
        exercised = [c for c in calls if c not in assertion_methods]
        assumptions: List[str] = []
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                if sub.func.attr in assertion_methods:
                    assumptions.append(ast.unparse(sub))
            elif isinstance(sub, ast.Assert):
                assumptions.append(ast.unparse(sub))

        end_line = getattr(node, "end_lineno", node.lineno)
        source_slice = "\n".join(lines[node.lineno - 1 : end_line])
        return TestSummary(
            test_name=node.name,
            file=rel_path,
            line_start=node.lineno,
            line_end=end_line,
            behavior_tested=f"Exercises {', '.join(exercised) or 'target module'} and verifies {len(assumptions)} assertion(s)",
            exercised_functions=exercised,
            expected_flow=exercised,
            encoded_assumptions=assumptions,
            source_code=source_slice,
        )

    def _build_repo_summary_md(
        self,
        modules: Dict[str, Any],
        functions: List[FunctionSummary],
        classes: List[ClassSummary],
        tests: List[TestSummary],
    ) -> str:
        out = [
            "# Repository Knowledge Summary",
            "",
            f"- **Modules Indexed**: {len(modules)}",
            f"- **Functions Summarized**: {len(functions)}",
            f"- **Classes Summarized**: {len(classes)}",
            f"- **Tests Indexed**: {len(tests)}",
            "",
            "## Modules",
        ]
        for mod_name, info in modules.items():
            out.append(
                f"- `{mod_name}` ({info['line_count']} lines) — functions: {', '.join(info['functions']) or 'none'}"
            )
        out.append("")
        out.append("## Functions")
        for fn in functions:
            out.append(
                f"- `{fn.file}::{fn.function}({', '.join(fn.inputs)}) -> {fn.outputs}`: {fn.purpose} (calls: {', '.join(fn.calls) or 'none'})"
            )
        return "\n".join(out) + "\n"

    def safe_edit(
        self,
        caller_role: str,
        rel_file: str,
        search_block: str,
        replace_block: str,
        files_modified_so_far: List[str],
    ) -> Dict[str, Any]:
        if caller_role.lower() == "planner":
            raise ContractViolationError(
                "CONTRACT VIOLATION: PlannerAgent attempted to invoke safe_edit. Planner DOES NOT edit code."
            )

        max_files = int(self.config.get("coding", {}).get("max_files_changed", 5))
        if rel_file not in files_modified_so_far and len(files_modified_so_far) >= max_files:
            raise ContractViolationError(
                f"CONTRACT VIOLATION: Attempted to modify more than coding.max_files_changed ({max_files})."
            )

        target_path = self.repo_path / rel_file
        if not target_path.exists():
            raise FileNotFoundError(f"Target file does not exist: {rel_file}")

        original = target_path.read_text(encoding="utf-8")
        if search_block not in original:
            return {
                "applied": False,
                "file": rel_file,
                "error": "search_block not found in target file",
            }

        updated = original.replace(search_block, replace_block, 1)
        try:
            ast.parse(updated, filename=rel_file)
        except SyntaxError as exc:
            return {
                "applied": False,
                "file": rel_file,
                "error": f"SyntaxError in proposed edit: {exc}",
            }

        target_path.write_text(updated, encoding="utf-8")
        return {
            "applied": True,
            "file": rel_file,
            "diff": self.compute_unified_diff(rel_file),
        }

    def compute_unified_diff(self, rel_file: Optional[str] = None) -> str:
        diffs: List[str] = []
        targets = [rel_file] if rel_file else sorted(self._file_snapshots.keys())
        for rel in targets:
            if rel not in self._file_snapshots:
                continue
            before = self._file_snapshots[rel].splitlines(keepends=True)
            after_path = self.repo_path / rel
            if not after_path.exists():
                continue
            after = after_path.read_text(encoding="utf-8").splitlines(keepends=True)
            if before != after:
                diff_lines = difflib.unified_diff(
                    before,
                    after,
                    fromfile=f"a/{rel}",
                    tofile=f"b/{rel}",
                )
                diffs.append("".join(diff_lines))
        return "\n".join(diffs)
