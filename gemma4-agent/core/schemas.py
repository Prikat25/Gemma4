"""Strict data contracts and schemas enforced by the Gemma 4 SWE Agent backend."""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


class ContractViolationError(RuntimeError):
    """Raised when an agent or tool violates an explicit manifest prohibition."""


@dataclass
class FunctionSummary:
    function: str
    file: str
    line_start: int
    line_end: int
    inputs: List[str]
    outputs: str
    purpose: str
    calls: List[str]
    called_by: List[str] = field(default_factory=list)
    side_effects: List[str] = field(default_factory=list)
    important_logic: List[str] = field(default_factory=list)
    source_code: str = ""

    def to_dict(self, include_source: bool = False) -> Dict[str, Any]:
        data = asdict(self)
        if not include_source:
            data.pop("source_code", None)
        return data


@dataclass
class ClassSummary:
    class_name: str
    file: str
    line_start: int
    line_end: int
    bases: List[str]
    methods: List[str]
    purpose: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TestSummary:
    test_name: str
    file: str
    line_start: int
    line_end: int
    behavior_tested: str
    exercised_functions: List[str]
    expected_flow: List[str]
    encoded_assumptions: List[str]
    source_code: str = ""

    def to_dict(self, include_source: bool = False) -> Dict[str, Any]:
        data = asdict(self)
        if not include_source:
            data.pop("source_code", None)
        return data


@dataclass
class BugRecord:
    bug_id: str
    issue_pattern: str
    repository_pattern: str
    symptoms: List[str]
    relevant_functions: List[str]
    fix_pattern: str
    patch: str
    outcome: str
    similarity_score: float = 0.0
    epistemic_status: str = "SIMILARITY_IS_EVIDENCE_NOT_TRUTH"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PlanArtifact:
    problem: str
    evidence: List[str]
    root_cause_hypothesis: str
    affected_functions: List[str]
    expected_flow: List[str]
    actual_flow: List[str]
    changes_required: List[str]
    files_to_modify: List[str]
    tests_to_run: List[str]
    risk: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FailureAnalysisArtifact:
    failure_type: str
    likely_function: str
    hypothesis: str
    evidence: List[str]
    recommended_action: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LoggerState:
    """Structured state owned by the backend LoggerAgent. No prose invention allowed."""

    task: str
    current_phase: str = "initialization"
    experiment_id: str = "E5"
    hypothesis: str = ""
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    files_inspected: List[str] = field(default_factory=list)
    functions_inspected: List[str] = field(default_factory=list)
    tests_run: List[Dict[str, Any]] = field(default_factory=list)
    failures: List[Dict[str, Any]] = field(default_factory=list)
    changes: List[Dict[str, Any]] = field(default_factory=list)
    remaining_questions: List[str] = field(default_factory=list)
    complexity_estimate: Dict[str, Any] = field(default_factory=dict)
    time_budget: Dict[str, Any] = field(default_factory=dict)
    active_capabilities: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
