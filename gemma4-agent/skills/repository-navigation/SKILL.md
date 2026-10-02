---
name: repository-navigation
description: Guidance on using competition harness graph, embedding, and file reading tools to localize code quickly.
---

# Repository Navigation Skill

## Navigation Strategy
When given a new repository and issue:
1. **Find entry symbols**: Call `search_similar_code` with key terms from the issue to locate candidate files.
2. **Trace callers/callees**: Call `get_code_neighbors` on suspected functions to understand what invokes them.
3. **Inspect subgraphs**: Call `get_code_subgraph` when navigating a deep module or class hierarchy.
4. **Read full definitions**: Use `read_file` to inspect the exact lines of code where the logic executes.
5. **Verify git status**: Call `get_status` to understand current workspace state.
