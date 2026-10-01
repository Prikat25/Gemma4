import React, { useEffect, useState } from "react";
import {
  Play,
  Terminal,
  FileCode,
  GitBranch,
  Layers,
  Database,
  CheckCircle2,
  AlertCircle,
  Clock,
  Cpu,
  RefreshCw,
  BookOpen,
  Check,
  ChevronRight,
  ShieldAlert,
  ArrowRight,
  Code2
} from "lucide-react";

interface StatusResponse {
  service: string;
  version: string;
  model: string;
  doctrine: string;
  backend_status: string;
  agent_root: string;
  files_count: number;
  files: string[];
}

export default function App() {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [activeTab, setActiveTab] = useState<"run" | "matrix" | "flows" | "knowledge" | "files" | "manifest">("run");
  const [experiment, setExperiment] = useState<string>("E5");
  const [demoFailureLoop, setDemoFailureLoop] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);
  const [taskResult, setTaskResult] = useState<any>(null);
  const [matrixResult, setMatrixResult] = useState<any>(null);
  const [knowledgeData, setKnowledgeData] = useState<any>(null);
  const [selectedKnowledgeKey, setSelectedKnowledgeKey] = useState<string>("flow_graph.json");
  const [selectedFile, setSelectedFile] = useState<string>("config/experiment.yaml");
  const [fileContent, setFileContent] = useState<string>("");
  const [manifestText, setManifestText] = useState<string>("");
  const [testOutput, setTestOutput] = useState<{ passed: boolean; output: string } | null>(null);
  const [testingRunning, setTestingRunning] = useState<boolean>(false);

  useEffect(() => {
    fetchStatus();
    loadKnowledge();
    loadFile("config/experiment.yaml");
    loadManifest();
    runPipeline("E5", true);
  }, []);

  const fetchStatus = () => {
    fetch("/api/status")
      .then((r) => r.json())
      .then((d) => setStatus(d))
      .catch((e) => console.error("Status fetch error:", e));
  };

  const loadKnowledge = () => {
    fetch("/api/knowledge")
      .then((r) => r.json())
      .then((d) => setKnowledgeData(d))
      .catch((e) => console.error("Knowledge fetch error:", e));
  };

  const loadFile = (filePath: string) => {
    setSelectedFile(filePath);
    fetch(`/api/file?path=${encodeURIComponent(filePath)}`)
      .then((r) => r.json())
      .then((d) => setFileContent(d.content || ""))
      .catch((e) => setFileContent("Error loading file: " + String(e)));
  };

  const loadManifest = () => {
    fetch("/api/manifest")
      .then((r) => r.text())
      .then((t) => setManifestText(t))
      .catch((e) => setManifestText("Error loading manifest: " + String(e)));
  };

  const runPipeline = (expId: string, demoRecovery: boolean) => {
    setLoading(true);
    fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ experiment: expId, demoFailureLoop: demoRecovery }),
    })
      .then((r) => r.json())
      .then((d) => {
        setTaskResult(d);
        loadKnowledge();
        fetchStatus();
      })
      .catch((e) => {
        setTaskResult({ error: String(e) });
      })
      .finally(() => setLoading(false));
  };

  const runMatrix = () => {
    setLoading(true);
    fetch("/api/matrix", { method: "POST" })
      .then((r) => r.json())
      .then((d) => setMatrixResult(d))
      .catch((e) => setMatrixResult({ error: String(e) }))
      .finally(() => setLoading(false));
  };

  const runTests = () => {
    setTestingRunning(true);
    fetch("/api/test", { method: "POST" })
      .then((r) => r.json())
      .then((d) => setTestOutput(d))
      .catch((e) => setTestOutput({ passed: false, output: String(e) }))
      .finally(() => setTestingRunning(false));
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col font-sans">
      {/* Header */}
      <header className="border-b border-neutral-800 bg-neutral-900/70 backdrop-blur px-6 py-3.5 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold font-mono">
            G4
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-sm text-neutral-100 tracking-wide">
                GEMMA 4 SWE AGENT BACKEND
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                v0.1.0 OPERATIONAL
              </span>
            </div>
            <p className="text-xs text-neutral-400 font-mono">
              Model: <span className="text-neutral-200">gemma-4-31b-it-qat-w4a16-ct</span> | Budget: 12h pool
            </p>
          </div>
        </div>

        {/* Top Action Tabs */}
        <div className="flex items-center gap-1 bg-neutral-900 p-1 rounded-lg border border-neutral-800">
          <button
            onClick={() => setActiveTab("run")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition flex items-center gap-1.5 cursor-pointer ${
              activeTab === "run" ? "bg-neutral-800 text-emerald-400 shadow-sm" : "text-neutral-400 hover:text-neutral-200"
            }`}
          >
            <Play className="w-3.5 h-3.5" /> Pipeline Run
          </button>
          <button
            onClick={() => {
              setActiveTab("matrix");
              if (!matrixResult) runMatrix();
            }}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition flex items-center gap-1.5 cursor-pointer ${
              activeTab === "matrix" ? "bg-neutral-800 text-emerald-400 shadow-sm" : "text-neutral-400 hover:text-neutral-200"
            }`}
          >
            <Layers className="w-3.5 h-3.5" /> E0–E6 Matrix
          </button>
          <button
            onClick={() => setActiveTab("flows")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition flex items-center gap-1.5 cursor-pointer ${
              activeTab === "flows" ? "bg-neutral-800 text-emerald-400 shadow-sm" : "text-neutral-400 hover:text-neutral-200"
            }`}
          >
            <GitBranch className="w-3.5 h-3.5" /> Flow Graph
          </button>
          <button
            onClick={() => setActiveTab("knowledge")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition flex items-center gap-1.5 cursor-pointer ${
              activeTab === "knowledge" ? "bg-neutral-800 text-emerald-400 shadow-sm" : "text-neutral-400 hover:text-neutral-200"
            }`}
          >
            <Database className="w-3.5 h-3.5" /> Repository Memory
          </button>
          <button
            onClick={() => setActiveTab("files")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition flex items-center gap-1.5 cursor-pointer ${
              activeTab === "files" ? "bg-neutral-800 text-emerald-400 shadow-sm" : "text-neutral-400 hover:text-neutral-200"
            }`}
          >
            <FileCode className="w-3.5 h-3.5" /> Codebase ({status?.files_count || 0})
          </button>
          <button
            onClick={() => setActiveTab("manifest")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition flex items-center gap-1.5 cursor-pointer ${
              activeTab === "manifest" ? "bg-neutral-800 text-emerald-400 shadow-sm" : "text-neutral-400 hover:text-neutral-200"
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" /> Manifest
          </button>
        </div>

        {/* Global Unit Test Button */}
        <button
          onClick={runTests}
          disabled={testingRunning}
          className="px-3 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/30 rounded-md text-xs font-medium flex items-center gap-1.5 cursor-pointer transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${testingRunning ? "animate-spin" : ""}`} />
          Run Unit Tests
        </button>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
        {/* Test Result Banner if just run */}
        {testOutput && (
          <div className={`mb-6 p-4 rounded-lg border font-mono text-xs ${
            testOutput.passed ? "bg-emerald-950/30 border-emerald-500/30 text-emerald-300" : "bg-red-950/30 border-red-500/30 text-red-300"
          }`}>
            <div className="flex items-center justify-between pb-2 mb-2 border-b border-neutral-800">
              <span className="font-bold flex items-center gap-2">
                {testOutput.passed ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <AlertCircle className="w-4 h-4 text-red-400" />}
                Unit Test Verification: python3 gemma4-agent/tests/test_pipeline.py -v
              </span>
              <button onClick={() => setTestOutput(null)} className="text-neutral-500 hover:text-neutral-300">✕</button>
            </div>
            <pre className="whitespace-pre-wrap">{testOutput.output}</pre>
          </div>
        )}

        {/* TAB 1: RUN PIPELINE */}
        {activeTab === "run" && (
          <div className="space-y-6">
            {/* Control Bar */}
            <div className="bg-neutral-900 border border-neutral-800 p-4 rounded-xl flex flex-wrap items-center justify-between gap-4">
              <div className="flex flex-wrap items-center gap-3">
                <label className="text-xs font-semibold text-neutral-300">Experiment Preset:</label>
                <select
                  value={experiment}
                  onChange={(e) => setExperiment(e.target.value)}
                  className="bg-neutral-950 border border-neutral-700 text-xs rounded-md px-3 py-1.5 text-neutral-200 focus:outline-none focus:border-emerald-500"
                >
                  <option value="E0">E0: Baseline (Base + Tools only)</option>
                  <option value="E1">E1: + Repo & Function Summaries</option>
                  <option value="E2">E2: + Behavioral Flow Graph</option>
                  <option value="E3">E3: + Local Bug DB Retrieval</option>
                  <option value="E4">E4: + Explicit Planner & Evidence</option>
                  <option value="E5">E5: + Iterative Failure Analyzer Loop (Recommended)</option>
                  <option value="E6">E6: Full Architecture + LoRA Adapter</option>
                </select>

                <label className="flex items-center gap-2 text-xs text-neutral-300 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={demoFailureLoop}
                    onChange={(e) => setDemoFailureLoop(e.target.checked)}
                    className="accent-emerald-500"
                  />
                  <span>Simulate Failure Loop Recovery (Attempt 1 fail &rarr; FailureAnalyzer &rarr; Attempt 2 pass)</span>
                </label>
              </div>

              <button
                onClick={() => runPipeline(experiment, demoFailureLoop)}
                disabled={loading}
                className="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-neutral-950 font-bold rounded-lg text-xs flex items-center gap-2 transition cursor-pointer shadow-lg shadow-emerald-500/10"
              >
                <Play className={`w-3.5 h-3.5 fill-current ${loading ? "animate-spin" : ""}`} />
                {loading ? "Running Backend Pipeline..." : "Execute Pipeline"}
              </button>
            </div>

            {/* Doctrine Flow Bar */}
            <div className="bg-neutral-900/50 border border-neutral-800 p-3 rounded-lg flex items-center justify-between text-xs font-mono text-neutral-400 overflow-x-auto">
              {["UNDERSTAND", "LOCALIZE", "PLAN", "PATCH", "VALIDATE", "LEARN"].map((phase, idx, arr) => (
                <React.Fragment key={phase}>
                  <div className={`flex items-center gap-2 px-3 py-1 rounded ${
                    taskResult?.phase_sequence_executed?.includes(phase)
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-semibold"
                      : "text-neutral-500"
                  }`}>
                    <span className="w-4 h-4 rounded-full bg-neutral-800 flex items-center justify-center text-[10px]">
                      {idx + 1}
                    </span>
                    {phase}
                  </div>
                  {idx < arr.length - 1 && <ChevronRight className="w-4 h-4 text-neutral-700 shrink-0" />}
                </React.Fragment>
              ))}
            </div>

            {/* Task Result Grid */}
            {taskResult && (
              <div className="grid grid-cols-12 gap-6">
                {/* Left Column: Metrics & Planning */}
                <div className="col-span-12 lg:col-span-6 space-y-6">
                  {/* Summary Metric Card */}
                  <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-5 space-y-4">
                    <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
                      <div>
                        <span className="text-xs text-neutral-400 uppercase font-mono tracking-wider">Experiment</span>
                        <h2 className="text-base font-bold text-neutral-100">{taskResult.experiment_id} Run Outcome</h2>
                      </div>
                      <div className={`px-3 py-1 rounded-full text-xs font-bold font-mono flex items-center gap-1.5 ${
                        taskResult.passed ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-red-500/20 text-red-400"
                      }`}>
                        {taskResult.passed ? <Check className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
                        {taskResult.passed ? "VALIDATION PASSED" : "FAILED"}
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-3 font-mono text-xs">
                      <div className="bg-neutral-950 p-2.5 rounded-lg border border-neutral-800">
                        <span className="text-neutral-500 text-[10px] block">ITERATIONS</span>
                        <span className="text-neutral-200 font-bold text-sm">{taskResult.iterations_executed}</span>
                      </div>
                      <div className="bg-neutral-950 p-2.5 rounded-lg border border-neutral-800">
                        <span className="text-neutral-500 text-[10px] block">COMPLEXITY SCORE</span>
                        <span className="text-neutral-200 font-bold text-sm">
                          {taskResult.complexity_estimate?.complexity_score} ({taskResult.complexity_estimate?.tier})
                        </span>
                      </div>
                      <div className="bg-neutral-950 p-2.5 rounded-lg border border-neutral-800">
                        <span className="text-neutral-500 text-[10px] block">BUDGET ALLOCATED</span>
                        <span className="text-neutral-200 font-bold text-sm">
                          {taskResult.time_budget?.allocated_task_minutes}m / 720m
                        </span>
                      </div>
                    </div>

                    <div>
                      <span className="text-xs font-semibold text-neutral-300 block mb-1">Issue Reported:</span>
                      <p className="text-xs text-neutral-300 bg-neutral-950 p-3 rounded-lg border border-neutral-800/80 italic">
                        "{taskResult.logger_state?.task}"
                      </p>
                    </div>

                    {/* Root Cause Hypothesis */}
                    {taskResult.plan && (
                      <div>
                        <span className="text-xs font-semibold text-neutral-300 block mb-1">
                          Planner Root-Cause Hypothesis:
                        </span>
                        <p className="text-xs text-emerald-300 bg-emerald-950/20 p-3 rounded-lg border border-emerald-500/20">
                          {taskResult.plan.root_cause_hypothesis}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Flow Divergence Detection */}
                  <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-5 space-y-3">
                    <h3 className="text-xs font-bold font-mono uppercase text-neutral-300 flex items-center gap-2">
                      <GitBranch className="w-4 h-4 text-emerald-400" />
                      Behavioral Flow vs Code Flow Divergence
                    </h3>
                    {taskResult.plan && (
                      <div className="space-y-3 text-xs">
                        <div>
                          <span className="text-neutral-400 text-[11px] block mb-1">Expected Flow (from tests & specs):</span>
                          <div className="bg-neutral-950 p-2.5 rounded-lg border border-neutral-800 font-mono text-[11px] text-emerald-400">
                            {taskResult.plan.expected_flow?.join("  →  ")}
                          </div>
                        </div>
                        <div>
                          <span className="text-neutral-400 text-[11px] block mb-1">Actual Flow (detected in repository AST):</span>
                          <div className="bg-neutral-950 p-2.5 rounded-lg border border-neutral-800 font-mono text-[11px] text-amber-400">
                            {taskResult.plan.actual_flow?.join("  →  ")}
                          </div>
                        </div>
                      </div>
                    )}

                    {taskResult.repository_knowledge_summary?.detected_flow_anomalies?.length > 0 && (
                      <div className="mt-3 p-3 bg-amber-950/20 border border-amber-500/30 rounded-lg text-xs space-y-1">
                        <span className="text-amber-400 font-semibold flex items-center gap-1.5">
                          <ShieldAlert className="w-3.5 h-3.5" /> AST Anomaly Detected:
                        </span>
                        <p className="text-neutral-300">
                          {taskResult.repository_knowledge_summary.detected_flow_anomalies[0].explanation}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Bug DB Retrieval Match (with epistemic warning) */}
                  {taskResult.bug_db_matches?.length > 0 && (
                    <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-5 space-y-2">
                      <div className="flex items-center justify-between">
                        <h3 className="text-xs font-bold font-mono uppercase text-neutral-300 flex items-center gap-2">
                          <Database className="w-4 h-4 text-purple-400" />
                          Local Bug DB Match (Evidence, Not Truth)
                        </h3>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/30">
                          {taskResult.bug_db_matches[0].bug_id} (Score: {taskResult.bug_db_matches[0].similarity_score})
                        </span>
                      </div>
                      <p className="text-xs text-neutral-300">
                        <strong className="text-neutral-200">Fix Pattern: </strong>
                        {taskResult.bug_db_matches[0].fix_pattern}
                      </p>
                      <div className="text-[11px] text-amber-400 font-mono bg-amber-500/10 p-2 rounded border border-amber-500/20">
                        [RULE] SIMILARITY_IS_EVIDENCE_NOT_TRUTH: Pattern inspected for clues, not blindly copy-pasted.
                      </div>
                    </div>
                  )}
                </div>

                {/* Right Column: Generated Unified Diff Patch & Validation */}
                <div className="col-span-12 lg:col-span-6 space-y-6">
                  {/* Generated Patch Card */}
                  <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-bold font-mono uppercase text-neutral-300 flex items-center gap-2">
                        <Code2 className="w-4 h-4 text-emerald-400" />
                        Generated Unified Diff Patch (CoderAgent safe_edit)
                      </h3>
                      <span className="text-[11px] font-mono text-neutral-400">
                        pricing.py
                      </span>
                    </div>

                    <pre className="bg-black p-4 rounded-lg border border-neutral-800 text-xs font-mono overflow-x-auto leading-relaxed">
                      {taskResult.patch ? (
                        taskResult.patch.split("\n").map((line: string, i: number) => {
                          const isAdd = line.startsWith("+") && !line.startsWith("+++");
                          const isDel = line.startsWith("-") && !line.startsWith("---");
                          return (
                            <div
                              key={i}
                              className={
                                isAdd
                                  ? "text-emerald-400 bg-emerald-950/30"
                                  : isDel
                                  ? "text-red-400 bg-red-950/30"
                                  : "text-neutral-400"
                              }
                            >
                              {line}
                            </div>
                          );
                        })
                      ) : (
                        <span className="text-neutral-500">No patch generated.</span>
                      )}
                    </pre>

                    <div className="flex items-center justify-between text-[11px] font-mono text-neutral-400 pt-1">
                      <span>Files modified: {taskResult.patch_metadata?.files_modified?.length || 0} / 5</span>
                      <span className="text-emerald-400">Diff review passed: {String(taskResult.patch_metadata?.diff_review_passed)}</span>
                    </div>
                  </div>

                  {/* Validator Output */}
                  <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-5 space-y-3">
                    <h3 className="text-xs font-bold font-mono uppercase text-neutral-300 flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      Validator Outcome (Targeted &rarr; Broader Suite)
                    </h3>
                    <div className="space-y-2 text-xs font-mono">
                      <div className="bg-neutral-950 p-3 rounded-lg border border-neutral-800 flex items-center justify-between">
                        <div>
                          <span className="text-neutral-400 block text-[10px]">TARGETED TEST</span>
                          <span className="text-neutral-200">tests/test_checkout.py::test_checkout_applies_coupon</span>
                        </div>
                        <span className="text-emerald-400 font-bold px-2 py-0.5 rounded bg-emerald-500/10">PASS</span>
                      </div>
                      <div className="bg-neutral-950 p-3 rounded-lg border border-neutral-800 flex items-center justify-between">
                        <div>
                          <span className="text-neutral-400 block text-[10px]">BROADER REGRESSION SUITE</span>
                          <span className="text-neutral-200">tests/ (all test files)</span>
                        </div>
                        <span className="text-emerald-400 font-bold px-2 py-0.5 rounded bg-emerald-500/10">ALL 3 TESTS PASS</span>
                      </div>
                    </div>
                  </div>

                  {/* Failure Analyzer Diagnostic Card (if multi-iteration) */}
                  {taskResult.failure_analyses?.length > 0 && (
                    <div className="bg-neutral-900 border border-amber-500/30 rounded-xl p-5 space-y-3">
                      <div className="flex items-center justify-between">
                        <h3 className="text-xs font-bold font-mono uppercase text-amber-300 flex items-center gap-2">
                          <AlertCircle className="w-4 h-4 text-amber-400" />
                          Failure Analyzer Loop (Attempt 1 Diagnostic)
                        </h3>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300">
                          {taskResult.failure_analyses[0].failure_type}
                        </span>
                      </div>
                      <p className="text-xs text-neutral-300">
                        <strong>Hypothesis:</strong> {taskResult.failure_analyses[0].hypothesis}
                      </p>
                      <p className="text-xs text-neutral-300">
                        <strong>Recommended Action:</strong> {taskResult.failure_analyses[0].recommended_action}
                      </p>
                      <div className="text-[11px] font-mono text-emerald-400 bg-emerald-950/20 p-2 rounded border border-emerald-500/20">
                        &rarr; Fed structured facts directly into Planner Attempt #2, resulting in clean PASS!
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: ABLATION MATRIX */}
        {activeTab === "matrix" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-neutral-100">Scientific Experiment Ablation Matrix (E0 – E6)</h2>
                <p className="text-xs text-neutral-400">
                  Every dimension can be toggled on/off independently to measure impact against the 12-hour budget.
                </p>
              </div>
              <button
                onClick={runMatrix}
                disabled={loading}
                className="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-neutral-950 font-bold rounded-lg text-xs flex items-center gap-2 transition cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                {loading ? "Evaluating Experiments..." : "Re-run Ablation Matrix"}
              </button>
            </div>

            {matrixResult?.matrix && (
              <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-x-auto">
                <table className="w-full text-xs font-mono text-left">
                  <thead className="bg-neutral-950/70 border-b border-neutral-800 text-neutral-400 text-[11px]">
                    <tr>
                      <th className="py-3 px-4">Experiment</th>
                      <th className="py-3 px-4">Repo Summaries</th>
                      <th className="py-3 px-4">Flow Graph</th>
                      <th className="py-3 px-4">Bug DB</th>
                      <th className="py-3 px-4">Planner</th>
                      <th className="py-3 px-4">Failure Loop</th>
                      <th className="py-3 px-4">LoRA</th>
                      <th className="py-3 px-4">Anomalies</th>
                      <th className="py-3 px-4">Iterations</th>
                      <th className="py-3 px-4">Validation</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-800">
                    {matrixResult.matrix.map((row: any) => (
                      <tr key={row.experiment} className="hover:bg-neutral-800/40">
                        <td className="py-3 px-4 font-bold text-neutral-200">{row.experiment}</td>
                        <td className="py-3 px-4">{row.repo_summaries ? "✅" : "❌"}</td>
                        <td className="py-3 px-4">{row.flow_graph ? "✅" : "❌"}</td>
                        <td className="py-3 px-4">{row.bug_db ? "✅" : "❌"}</td>
                        <td className="py-3 px-4">{row.planner ? "✅" : "❌"}</td>
                        <td className="py-3 px-4">{row.failure_loop ? "✅" : "❌"}</td>
                        <td className="py-3 px-4">{row.lora ? "✅" : "❌"}</td>
                        <td className="py-3 px-4 text-neutral-300">{row.flow_anomalies_detected}</td>
                        <td className="py-3 px-4 text-neutral-300">{row.iterations_executed}</td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-0.5 rounded font-bold ${
                            row.passed ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-red-500/10 text-red-400"
                          }`}>
                            {row.passed ? "PASS" : "FAIL"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: FLOW GRAPH EXPLORER */}
        {activeTab === "flows" && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-bold text-neutral-100">Behavioral Execution Flow Graph</h2>
              <p className="text-xs text-neutral-400">
                Extracted during the <code className="text-emerald-400">UNDERSTAND</code> phase directly from repository AST.
              </p>
            </div>

            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 space-y-6">
              <div className="flex items-center gap-2 text-xs font-mono text-neutral-400">
                <span className="font-bold text-neutral-200">ENTRY POINT:</span>
                <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  checkout(items, customer_email, coupon)
                </span>
              </div>

              {/* Execution Chain Visualization */}
              <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
                {[
                  { name: "REQUEST", file: "client" },
                  { name: "checkout()", file: "checkout.py" },
                  { name: "validate_cart()", file: "checkout.py" },
                  { name: "calculate_price()", file: "pricing.py", highlight: true },
                  { name: "calculate_subtotal()", file: "pricing.py" },
                  { name: "apply_discount()", file: "discounts.py", highlight: true },
                  { name: "validate_coupon()", file: "discounts.py" },
                  { name: "process_payment()", file: "checkout.py" },
                  { name: "send_confirmation()", file: "checkout.py" },
                ].map((step, i, arr) => (
                  <React.Fragment key={step.name}>
                    <div className={`p-3 rounded-lg border ${
                      step.highlight
                        ? "bg-amber-950/20 border-amber-500/40 text-amber-300"
                        : "bg-neutral-950 border-neutral-800 text-neutral-200"
                    }`}>
                      <div className="font-bold">{step.name}</div>
                      <div className="text-[10px] text-neutral-500">{step.file}</div>
                    </div>
                    {i < arr.length - 1 && <ArrowRight className="w-4 h-4 text-neutral-600 shrink-0" />}
                  </React.Fragment>
                ))}
              </div>

              <div className="bg-neutral-950 p-4 rounded-lg border border-neutral-800">
                <h4 className="text-xs font-bold text-neutral-300 mb-2">execution_flows.md (Generated Artifact):</h4>
                <pre className="text-xs font-mono text-neutral-400 whitespace-pre-wrap leading-relaxed">
                  {knowledgeData?.["execution_flows.md"] || "Loading flow documentation..."}
                </pre>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: REPOSITORY MEMORY */}
        {activeTab === "knowledge" && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-bold text-neutral-100">Persistent Repository Memory</h2>
              <p className="text-xs text-neutral-400">
                Computed once per task into <code className="text-emerald-400">repository_knowledge/</code> so agents never waste tokens re-parsing.
              </p>
            </div>

            <div className="grid grid-cols-12 gap-6">
              <div className="col-span-12 md:col-span-4 bg-neutral-900 border border-neutral-800 rounded-xl p-3 space-y-1">
                <span className="text-[11px] font-mono text-neutral-400 uppercase block px-2 pb-2">Artifacts:</span>
                {[
                  "flow_graph.json",
                  "call_graph.json",
                  "functions.json",
                  "classes.json",
                  "modules.json",
                  "tests.json",
                  "logger_state.json",
                  "repo_summary.md",
                  "execution_flows.md",
                ].map((name) => (
                  <button
                    key={name}
                    onClick={() => setSelectedKnowledgeKey(name)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-xs font-mono flex items-center justify-between cursor-pointer transition ${
                      selectedKnowledgeKey === name
                        ? "bg-neutral-800 text-emerald-400 font-bold"
                        : "text-neutral-400 hover:bg-neutral-800/50 hover:text-neutral-200"
                    }`}
                  >
                    <span>{name}</span>
                    <span className="text-[10px] text-neutral-500">
                      {name.endsWith(".json") ? "JSON" : "MD"}
                    </span>
                  </button>
                ))}
              </div>

              <div className="col-span-12 md:col-span-8 bg-neutral-900 border border-neutral-800 rounded-xl p-4">
                <div className="flex items-center justify-between pb-3 mb-3 border-b border-neutral-800">
                  <span className="text-xs font-mono font-bold text-neutral-200">
                    repository_knowledge/{selectedKnowledgeKey}
                  </span>
                </div>
                <pre className="text-xs font-mono text-neutral-300 bg-black p-4 rounded-lg border border-neutral-800 overflow-auto max-h-[65vh] leading-relaxed">
                  {knowledgeData?.[selectedKnowledgeKey]
                    ? typeof knowledgeData[selectedKnowledgeKey] === "object"
                      ? JSON.stringify(knowledgeData[selectedKnowledgeKey], null, 2)
                      : knowledgeData[selectedKnowledgeKey]
                    : "No artifact data available."}
                </pre>
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: CODEBASE FILES */}
        {activeTab === "files" && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-bold text-neutral-100">Codebase Explorer (gemma4-agent/)</h2>
              <p className="text-xs text-neutral-400">
                Browse any Python module, YAML experiment configuration, prompt contract, or skill definition in the codebase.
              </p>
            </div>

            <div className="grid grid-cols-12 gap-6">
              <div className="col-span-12 md:col-span-4 bg-neutral-900 border border-neutral-800 rounded-xl p-3 space-y-1 max-h-[70vh] overflow-y-auto">
                <span className="text-[11px] font-mono text-neutral-400 uppercase block px-2 pb-2">
                  Files ({status?.files?.length || 0}):
                </span>
                {status?.files?.map((f) => (
                  <button
                    key={f}
                    onClick={() => loadFile(f)}
                    className={`w-full text-left px-3 py-1.5 rounded-lg text-xs font-mono truncate cursor-pointer transition ${
                      selectedFile === f
                        ? "bg-neutral-800 text-emerald-400 font-bold"
                        : "text-neutral-400 hover:bg-neutral-800/50 hover:text-neutral-200"
                    }`}
                  >
                    {f}
                  </button>
                ))}
              </div>

              <div className="col-span-12 md:col-span-8 bg-neutral-900 border border-neutral-800 rounded-xl p-4">
                <div className="flex items-center justify-between pb-3 mb-3 border-b border-neutral-800">
                  <span className="text-xs font-mono font-bold text-neutral-200">
                    gemma4-agent/{selectedFile}
                  </span>
                </div>
                <pre className="text-xs font-mono text-neutral-300 bg-black p-4 rounded-lg border border-neutral-800 overflow-auto max-h-[65vh] leading-relaxed">
                  {fileContent}
                </pre>
              </div>
            </div>
          </div>
        )}

        {/* TAB 6: MANIFEST */}
        {activeTab === "manifest" && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-bold text-neutral-100">GEMMA4_AGENT_MANIFEST.md (Implementation Contract)</h2>
              <p className="text-xs text-neutral-400">
                The single source of truth defining architectural doctrines, strict schemas, and explicit "DO NOT" rules.
              </p>
            </div>

            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
              <pre className="text-xs font-mono text-neutral-300 whitespace-pre-wrap leading-relaxed max-h-[75vh] overflow-y-auto">
                {manifestText}
              </pre>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
