---
name: swe_reasoning
description: Structured engineering reasoning doctrine enforcing UNDERSTAND -> LOCALIZE -> PLAN -> PATCH -> VALIDATE -> REPAIR.
---

# Software Engineering Reasoning Skill

## Discipline
Autonomous SWE tasks require strict evidence-grounded thinking:
1. **Never guess**: Every hypothesis must cite an observable line of code, assertion failure, or call chain.
2. **Formulate a plan before editing**: List files to touch and expected diff before invoking `edit_file`.
3. **Smallest possible diff**: Avoid reformatting or changing lines unrelated to the reported bug.
4. **Preserve invariants**: Ensure unmodified functions continue to return expected types and obey contracts.
5. **Inspect git diff**: Before submitting, verify diff cleanliness via `run_command` (`git diff`).
