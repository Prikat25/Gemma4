# Function Summarizer Agent Prompt

Your task is to summarize a single extracted Python function or test into structured JSON for the persistent `repository_knowledge/` cache.

## Required JSON Schema (`FunctionSummary`)
```json
{
  "function": "string",
  "file": "string",
  "inputs": ["string"],
  "outputs": "string",
  "purpose": "Concise single-sentence description of behavior",
  "calls": ["string"],
  "called_by": ["string"],
  "side_effects": ["string"],
  "important_logic": ["ordered steps of key logic and branch conditions"]
}
```

## Constraints
- Base `calls`, `inputs`, and `important_logic` strictly on the AST and source body provided.
- Never hallucinate helper functions that do not appear in the body.
