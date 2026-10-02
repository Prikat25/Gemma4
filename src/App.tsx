export default function App() {
  return (
    <div style={{ maxWidth: 800, margin: "0 auto" }}>
      <h2 style={{ color: "#34d399", marginBottom: 8 }}>Google Gemma 4 Developer Agent</h2>
      <p style={{ color: "#a3a3a3", fontSize: 13, marginBottom: 16 }}>
        All competition agent configuration and assets are consolidated inside <code>gemma4-agent/</code>.
      </p>
      <pre style={{ background: "#171717", padding: 16, borderRadius: 8, fontSize: 12, overflow: "auto", border: "1px solid #262626" }}>
{`gemma4-agent/
├── agent.yaml              # Root ADK submission config (Model: gemma-4-31b-it-qat-w4a16-ct)
├── configs/
│   └── experiment.yaml     # Single master experiment variables
├── prompts/
│   ├── system.md           # Main SWE agent reasoning doctrine
│   └── researcher.md       # Read-only repository researcher
├── sub_agents/
│   └── repository_researcher.yaml
├── skills/
│   ├── swe_reasoning/
│   ├── repository_navigation/
│   ├── testing/
│   └── bug_patterns/
├── experiments/            # E0, E1, E2, E3, E4, E5, E6
├── harness/                # dev_tasks.jsonl, mock_harness.py, test_submission.py
└── package_submission.py   # Builds Kaggle submission.zip (agent.yaml at root)`}
      </pre>
    </div>
  );
}
