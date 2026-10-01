---
name: flow_analysis
description: Builds the two-layer Structural Call Graph and Behavioral Execution Flow Graph (`flow_analysis`).
---

# Flow Analysis Skill

## Capability: `flow_analysis`
Constructs:
1. `repository_knowledge/call_graph.json`: Direct caller/callee adjacency map.
2. `repository_knowledge/flow_graph.json`: Entry-point-to-leaf ordered execution chains (e.g. `checkout -> validate_cart -> calculate_price -> calculate_subtotal -> apply_discount -> process_payment -> send_confirmation`).
3. `repository_knowledge/execution_flows.md`: Human- and LLM-readable flow diagrams and divergence diagnostics.

## Tool Binding
Implemented in `tools/graph_tools.py`.
