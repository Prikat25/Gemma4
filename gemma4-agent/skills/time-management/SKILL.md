---
name: time_management
description: Task complexity estimation, dynamic 12-hour budget allocation, and context window trimming (`time_management`, `context_management`).
---

# Time & Context Management Skill

## Capabilities
- `time_management`: Computes `complexity = 0.30*files + 0.25*flow_depth + 0.20*tests + 0.15*deps + 0.10*issue_len` using configurable weights from `config/experiment.yaml`, assigns a dynamic time budget (`simple` / `medium` / `complex`), and enforces reserve budget limits across the 12-hour (720-minute) competition window.
- `context_management`: Enforces `max_function_summaries`, `max_tests`, `max_flow_nodes`, `max_bug_matches`, and `max_research_results` so context never overflows or dilutes reasoning.
