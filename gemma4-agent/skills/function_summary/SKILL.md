---
name: function_summary
description: Extracts and summarizes repository functions into structured JSON memory (`function_analysis`).
---

# Function Summary Skill

## Capability: `function_analysis`
Parses every function via Python `ast` and produces `repository_knowledge/functions.json` entries containing:
- `function`, `file`, `inputs`, `outputs`, `purpose`, `calls`, `called_by`, `side_effects`, `important_logic`.

## Caching Rule
Computed once during the `UNDERSTAND` phase and cached in `repository_knowledge/functions.json`.
