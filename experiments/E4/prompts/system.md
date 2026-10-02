# Experiment E4 Prompt: Mandatory PLAN Phase
Follow UNDERSTAND -> LOCALIZE -> PLAN -> PATCH -> VALIDATE.
You are STRICTLY REQUIRED to formulate an explicit internal plan before calling edit_file:
1. Identify exact root cause and failing assertion.
2. List files to touch and expected surgical change.
3. Apply patch with edit_file.
4. Verify with run_command.
5. Call submit_patch upon passing tests.
