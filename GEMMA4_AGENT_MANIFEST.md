# GEMMA 4 SWE AGENT — BACKEND IMPLEMENTATION MANIFEST (v0.1)

> ## **UNDERSTAND → LOCALIZE → PLAN → PATCH → VALIDATE → LEARN**
>
> **THE MODEL IS NOT THE SYSTEM.**
> `Gemma 4 31B IT QAT W4A16 CT` is the reasoning engine.
> The backend owns: **state, repository facts, workflow, tool execution, logging, validation, failure history, and time management.**
> The model proposes actions. The backend executes and verifies them.

---

## 1. Competition Objective & Target

Build an autonomous software-engineering agent around:
```text
Gemma 4 31B IT QAT W4A16 CT
```
that receives `Repository + Issue` and produces a `Patch` that passes hidden validation tests.

The competition evaluates patches using **PASS/FAIL validation**, and the overall score is the percentage of tasks whose patches pass. The total agent runtime budget is **12 hours (720 minutes)** across tasks, excluding patch validation.

```text
MAXIMIZE
    passed_tasks

SUBJECT TO
    12-hour total agent budget (720 minutes)
    Model constraints (gemma-4-31b-it-qat-w4a16-ct)
    Tool/harness sandbox constraints (offline-first evaluation)
    50% public / 50% private test split (strict anti-overfitting discipline)
```

---

## 2. Explicit "DO NOT" Rules (Contract Prohibitions)

1. **DO NOT allow the Model to own application state.** All state transitions are persisted deterministically in the backend `LoggerState` artifact.
2. **DO NOT allow `LoggerAgent` to invent facts or generate prose.** The Logger only records verified tool outputs, AST facts, model decisions, test outcomes, and repository observations.
3. **DO NOT allow `PlannerAgent` to edit or write source code.** Any file modification attempt during the `PLAN` phase raises an immediate `ContractViolationError`.
4. **DO NOT re-summarize unchanged functions across iterations or sub-agents.** AST extraction, function summaries, test summaries, and flow graphs are computed once per task and served from `repository_knowledge/`.
5. **DO NOT treat `BugLookup` matches as ground truth.** Historical bug records are injected strictly as scored evidence (`similarity_is_evidence_not_truth: true`) and never auto-applied without verification against the repository's actual flow graph.
6. **DO NOT rely on live internet access during evaluation.** The `ResearcherAgent` operates **local-first** following the strict 5-level evidence hierarchy:
   - **Level 1:** Repository source code & AST
   - **Level 2:** Repository test suite & assertions
   - **Level 3:** Function summaries & behavioral execution flow graph
   - **Level 4:** Local `bug_db` historical patterns
   - **Level 5:** Offline/cached external documentation (disabled by default in eval)
7. **DO NOT hardcode experiment toggles in Python code.** Every architectural capability (logger, function summarizer, flow graph, bug lookup, planner, researcher, validator, failure analyzer, LoRA) is switchable via `config/experiment.yaml` (supporting the E0–E6 ablation matrix).
8. **DO NOT enable LoRA blindly.** Because patched vLLM environments can exhibit duplicate decoder-layer registration issues where adapters load without influencing logits, `training.use_lora` defaults to `false` and requires a runtime activation sanity check when enabled.

---

## 3. Directory & Artifact Layout

```text
gemma4-agent/
├── GEMMA4_AGENT_MANIFEST.md
├── agent.yaml                        # Root competition agent definition & subagent wiring
├── cli.py                            # CLI runner for single tasks, E0-E6 ablations, and verification
├── config/
│   └── experiment.yaml               # Master configurable experiment variables
├── experiments/
│   ├── baseline.yaml                 # E0: Base + tools only (all extra capabilities OFF)
│   ├── summaries.yaml                # E1: + Repo & Function/Test summaries
│   ├── flow_graph.yaml               # E2: + Structural & Behavioral Flow Graph
│   ├── e3_bug_db.yaml                # E3: + Local Bug DB retrieval
│   ├── e4_planner.yaml               # E4: + Explicit Planner & Evidence requirement
│   ├── e5_failure_loop.yaml          # E5: + Iterative Validator & Failure Analyzer loop
│   └── lora.yaml                     # E6: Full architecture + LoRA adapter enabled
├── prompts/
│   ├── system.md
│   ├── function_summarizer.md
│   ├── planner.md
│   ├── coder.md
│   ├── researcher.md
│   └── failure_analyzer.md
├── skills/
│   ├── repository_analysis/
│   │   └── SKILL.md                  # repo_scan, class_analysis, dependency_analysis
│   ├── function_summary/
│   │   └── SKILL.md                  # function_analysis
│   ├── flow_analysis/
│   │   └── SKILL.md                  # flow_analysis
│   ├── bug_lookup/
│   │   └── SKILL.md                  # issue_analysis, bug_localization, bug_lookup, similar_fix_lookup
│   ├── coding/
│   │   └── SKILL.md                  # safe_edit, diff_review
│   ├── testing/
│   │   └── SKILL.md                  # test_analysis, run_targeted_test, run_test_suite, analyze_failure, regression_check
│   ├── logging/
│   │   └── SKILL.md                  # logging
│   └── time_management/
│       └── SKILL.md                  # time_management, context_management
├── core/
│   ├── __init__.py
│   ├── schemas.py                    # Strict JSON schemas & dataclasses for all artifacts
│   ├── config_loader.py              # YAML parser & E0-E6 preset loader
│   ├── model_client.py               # Gemma 4 31B IT QAT client + LoRA layer verifier
│   ├── agents.py                     # Supervisor, Logger, Summarizer, BugLookup, Researcher, Planner, Coder, Validator, FailureAnalyzer
│   └── pipeline.py                   # Enforces UNDERSTAND -> LOCALIZE -> PLAN -> PATCH -> VALIDATE -> LEARN
├── tools/
│   ├── __init__.py
│   ├── repo_tools.py                 # AST parser, function/class/test extraction, cache manager, safe_edit, diff_review
│   ├── graph_tools.py                # Two-layer Call Graph (structural) + Flow Graph (behavioral execution)
│   ├── bug_db.py                     # Local Bug DB engine with token/structural similarity
│   └── evaluation_tools.py           # Pytest/unittest runner, complexity estimator, time & context budget managers
├── knowledge/
│   └── bug_db/
│       └── seed_bugs.json            # Curated local bug patterns & outcomes
├── repository_knowledge/             # Dynamically generated & cached per task
│   ├── repo_summary.md
│   ├── functions.json
│   ├── classes.json
│   ├── modules.json
│   ├── tests.json
│   ├── call_graph.json
│   ├── flow_graph.json
│   └── execution_flows.md
└── sample_repo/                      # Reference repository with coupon discount bug for verification
```

---

## 4. Scientific Experiment Matrix (E0 – E6)

| Experiment ID | Config File | Repo Summaries | Flow Graph | Bug DB | Planner | Failure Loop | LoRA |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **E0** | `experiments/baseline.yaml` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **E1** | `experiments/summaries.yaml` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **E2** | `experiments/flow_graph.yaml` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **E3** | `experiments/e3_bug_db.yaml` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **E4** | `experiments/e4_planner.yaml` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| **E5** | `experiments/e5_failure_loop.yaml` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **E6** | `experiments/lora.yaml` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
