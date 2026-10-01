---
name: coding
description: Applies surgical source code edits and performs unified diff review (`safe_edit`, `diff_review`).
---

# Coding Skill

## Capabilities
- `safe_edit`: Verifies that the current agent role is `CoderAgent` (raises `ContractViolationError` if invoked by `PlannerAgent`), checks `coding.max_files_changed`, creates an automatic rollback snapshot, and applies the edit.
- `diff_review`: Generates a standard unified `git diff` patch and verifies syntax validity (`ast.parse`) and scope constraints before passing to Validator.
