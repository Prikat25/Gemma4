---
name: repository-analysis
description: Scans repository structure, extracts modules, classes, and import dependencies (`repo_scan`, `class_analysis`, `dependency_analysis`).
---

# Repository Analysis Skill

## Capabilities
- `repo_scan`: Walks repository tree (excluding `.git`, `__pycache__`, `.venv`), indexing Python modules and test files.
- `class_analysis`: Extracts class hierarchies, methods, and attributes into `repository_knowledge/classes.json`.
- `dependency_analysis`: Maps intra-repository imports into `repository_knowledge/modules.json`.