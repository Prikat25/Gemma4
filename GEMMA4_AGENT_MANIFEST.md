# GEMMA 4 SWE AGENT — KAGGLE ADK IMPLEMENTATION MANIFEST (v1.0)

> ## **UNDERSTAND → LOCALIZE → PLAN → PATCH → VALIDATE → LEARN/REPAIR**
>
> **THE AGENT CONFIGURATION IS THE SUBMISSION.**
> The Kaggle competition harness (`swegemma` / `adk-submission` / `adk-eval-core`) compiles a declarative `agent.yaml` into an ADK agent inside an offline Linux sandbox.
> The runtime model is: `gemma-4-31b-it-qat-w4a16-ct`.
> Custom Python runner pipelines (e.g. `cli.py`, `core/pipeline.py`) are NOT executed by Kaggle.

---

## 1. Competition Constraints & Environment

```text
EVALUATION:
    Kaggle offline sandbox (Python 3.13, Git, pytest, pre-indexed code graph & embeddings)
    Total budget: 12 hours across tasks (excluding patch validation)
    Metric: resolution_rate = passed_tasks / total_tasks (PASS/FAIL)

MODEL:
    gemma-4-31b-it-qat-w4a16-ct (Instruction-tuned, W4A16 QAT)

OFFICIAL HARNESS TOOLS:
    1. run_command          - Execute bash commands, run pytest/unittest, inspect git diff
    2. read_file            - Read specific files and line slices
    3. edit_file            - Apply surgical search-and-replace edits
    4. write_file           - Write or overwrite files
    5. get_status           - Inspect modified files and sandbox state
    6. submit_patch         - Final submission of git diff upon successful validation
    7. search_similar_code  - Semantic embedding retrieval across repository
    8. get_code_neighbors   - Caller/callee dependency graph navigation
    9. get_code_subgraph    - Neighborhood subgraph discovery
```

---

## 2. Core Agent Architecture

```text
                        ┌────────────────────────────────────────┐
                        │        MAIN GEMMA 4 AGENT              │
                        │    (gemma-4-31b-it-qat-w4a16-ct)       │
                        │                                        │
                        │  Owns Full Issue-Solving Loop:        │
                        │  UNDERSTAND -> LOCALIZE -> PLAN ->    │
                        │  PATCH -> VALIDATE -> REPAIR          │
                        └───────────────────┬────────────────────┘
                                            │
                        ┌───────────────────┴────────────────────┐
                        │                                        │
                        ▼                                        ▼
             ┌──────────────────────┐               ┌──────────────────────────┐
             │ REPOSITORY RESEARCHER│               │      ADK SKILLS          │
             │   (AgentTool, R/O)   │               │                          │
             │                      │               │ • swe_reasoning          │
             │ • search_similar_code│               │ • repository_navigation  │
             │ • get_code_neighbors │               │ • testing                │
             │ • get_code_subgraph  │               │ • bug_patterns (offline) │
             │ • read_file          │               └──────────────────────────┘
             │ • skip_summarization │
             └──────────────────────┘
```

1. **Main Agent**:
   - Executes the complete workflow from problem comprehension to validation and patch submission.
   - Authorized to use all file and execution tools.
2. **Repository Researcher (`repository_researcher`)**:
   - Registered as an `agent_tools` sub-agent.
   - **Strictly read-only**: forbidden from editing or submitting files.
   - Navigates precomputed repository embeddings and code graphs to deliver compact, structured evidence back to the main agent.
3. **ADK Skills**:
   - Simple directory-based capabilities containing `SKILL.md` with YAML frontmatter `name: <skill-name>`.

---

## 3. Mandatory Reasoning Progression

The system prompt strictly prevents jumping directly from `issue -> edit`:

1. **UNDERSTAND**:
   - Read issue text and extract functional requirements.
   - Use `search_similar_code` and code graph tools to locate candidate files and entry points.
2. **LOCALIZE**:
   - Read relevant lines using `read_file`.
   - Run existing unit tests via `run_command` to reproduce failure.
   - Compare expected behavior against actual behavior.
3. **PLAN**:
   - Formulate internal plan: Root cause, Evidence, Files to modify, Minimal patch strategy, and Risks.
   - Offline bug patterns from `skills/bug_patterns/` are treated strictly as **evidence/hypotheses**, never auto-applied truth.
4. **PATCH**:
   - Apply minimal surgical diff using `edit_file`.
   - Never modify test assertions simply to force passes.
   - Never leave scratch files in `/workspace`.
5. **VALIDATE**:
   - Run targeted test first via `run_command`.
   - Run broader regression test suite.
   - Only call `submit_patch` after validation succeeds.
6. **LEARN / REPAIR (Failure Loop)**:
   - If tests fail, inspect traceback and assertion diffs.
   - Re-localize if needed, repair patch, and re-test (configurable `max_repair_iterations`).

---

## 4. Controlled Scientific Experiments Matrix (E0 – E6)

Each experiment is a standalone, packageable ADK configuration located in `experiments/<ID>/`:

| Exp | Description | Harness Graph Tools | Skills | Explicit Plan | Repair Loop | LoRA Adapter |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **E0** | Base Gemma + Basic File Tools | ❌ | ❌ | ❌ | ❌ | ❌ |
| **E1** | E0 + Semantic & Graph Navigation Tools | ✅ | ❌ | ❌ | ❌ | ❌ |
| **E2** | E1 + Structured UNDERSTAND/LOCALIZE | ✅ | ✅ | ❌ | ❌ | ❌ |
| **E3** | E2 + Offline Bug Patterns | ✅ | ✅ | ❌ | ❌ | ❌ |
| **E4** | E3 + Mandatory Explicit PLAN Phase | ✅ | ✅ | ✅ | ❌ | ❌ |
| **E5** | **Flagship**: E4 + Validation Repair Loop + Researcher AgentTool | ✅ | ✅ | ✅ | ✅ | ❌ |
| **E6** | E5 + Real PEFT LoRA Adapter *(Disabled until real weights exist)* | ✅ | ✅ | ✅ | ✅ | ⚠️ *(Real weights only)* |

### Strict LoRA Anti-Fake Policy
In accordance with competition rules:
- `adapter` in `agent.yaml` is set to `null` until trained weights exist:
  ```text
  adapters/<adapter_name>/
  ├── adapter_config.json
  └── adapter_model.safetensors
  ```
- Simulated Python checks or mock strings are strictly prohibited.

---

## 5. Submission Packaging Specification

The submission archive must be created via:
```bash
python3 package_submission.py --experiment E5 --output submission.zip
```

The resulting `submission.zip` must satisfy:
1. **`agent.yaml` is located at the ROOT of the archive.**
2. Root `agent.yaml` declares `model: "gemma-4-31b-it-qat-w4a16-ct"`.
3. All referenced prompt files (`prompts/`) and skills (`skills/`) exist inside the archive.
4. No `../` path traversal.
5. Does not require or rely on custom Python runners to execute inside Kaggle.
