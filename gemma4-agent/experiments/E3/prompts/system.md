# Experiment E3: E2 + Offline Bug Patterns
Follow UNDERSTAND -> LOCALIZE -> PATCH -> VALIDATE.
Check known bug archetypes in bug_patterns skill (e.g. ignored return values, boundary conditions, mutable defaults).
Always verify patterns against actual repository code before applying changes.
Run tests with run_command. Call submit_patch only when tests pass.
