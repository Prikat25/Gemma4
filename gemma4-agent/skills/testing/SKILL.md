---
name: testing
description: Extracts test semantics, executes targeted and full test suites, and parses failure traces (`test_analysis`, `run_targeted_test`, `run_test_suite`, `analyze_failure`, `regression_check`).
---

# Testing & Validation Skill

## Capabilities
- `test_analysis`: Maps each `test_*` function to the repository functions it exercises and the assertions it encodes (`repository_knowledge/tests.json`).
- `run_targeted_test`: Runs only the most relevant test(s) first (`validation.run_targeted_tests_first`).
- `run_test_suite` & `regression_check`: Runs the broader repository test suite once targeted tests pass (`validation.run_broader_tests_after_targeted`).
- `analyze_failure`: Extracts expected vs received assertion values and stack frames for `FailureAnalyzerAgent`.
