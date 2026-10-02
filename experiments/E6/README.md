# Experiment E6 — LoRA Adapter Policy

## Stated Objective & Constraint
Google's Gemma 4 Developer Agent competition explicitly encourages post-training Gemma 4 into an autonomous SWE agent. However, submission guidelines state that LoRA adapters are optional.

## Strict Anti-Fake Policy
- E6 is marked **DISABLED** (`adapter: null`) until real PEFT adapter files exist:
  ```text
  adapters/<adapter_name>/
  ├── adapter_config.json
  └── adapter_model.safetensors
  ```
- No simulated Python flags, no mock "PASSED_SINGLE_REGISTRATION" printouts, and no placeholder adapters are permitted.
- Once trained weights exist, point `adapter: <adapter_name>` in `agent.yaml`, and the official competition harness will load the PEFT weights into `gemma-4-31b-it-qat-w4a16-ct`.
