# Experiment E6 — LoRA Adapter Policy

## Stated Objective & Constraint
Google's Gemma 4 Developer Agent competition allows optional LoRA adapters.

## Strict Anti-Fake Policy
- E6 is marked **DISABLED** (`adapter: null`) until real PEFT adapter files exist:
  ```text
  adapters/<adapter_name>/
  ├── adapter_config.json
  └── adapter_model.safetensors
  ```
- Simulated Python checks or mock strings are strictly prohibited.
- Once trained weights exist, point `adapter: <adapter_name>` in `agent.yaml`.
