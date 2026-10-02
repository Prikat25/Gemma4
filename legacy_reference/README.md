# Legacy Reference Components

The files previously in `core/` and `tools/repo_tools.py` were part of the initial local prototype.

In the real Kaggle Gemma 4 Developer Agent competition, Kaggle:
1. Takes `submission.zip`
2. Reads `agent.yaml` at the root
3. Compiles it into an ADK agent using `swegemma` and `adk-submission`
4. Executes the agent using the official sandbox tools (`run_command`, `read_file`, `edit_file`, etc.)

These legacy files are kept for local reference only. No competition submission behavior relies on them.
