---
name: testing
description: Running targeted tests, interpreting test tracebacks, and performing regression checks in the sandbox.
---

# Testing & Validation Skill

## Testing Protocol
1. **Reproduce before patching**:
   - Run the relevant test command using `run_command` (e.g. `pytest tests/test_feature.py -k test_target` or `python3 -m unittest ...`).
   - Confirm the test fails with the expected symptom.
2. **Targeted verification after editing files and applying patch**:
   - Re-run the exact failing test to verify it now passes.
3. **Failure analysis**:
   - If tests fail, inspect the exact assertion error line (`Expected X, got Y`).
   - Do not modify test assertions to force tests to pass.
