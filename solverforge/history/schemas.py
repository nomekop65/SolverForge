from typing import Literal

from pydantic import BaseModel


ExperimentStatus = Literal[
    "ACCEPTED",
    "REJECTED",
    "FAILED_VERIFICATION",
    "FAILED_BENCHMARK",
]


class ExperimentRecord(BaseModel):
    experiment_id: str
    timestamp: str

    parent_id: str | None = None

    source_file: str
    candidate_file: str

    hypothesis_title: str
    hypothesis: str
    proposed_change: str
    confidence: str

    baseline_median: float

    candidate_median: float | None = None
    speedup: float | None = None
    runtime_change_percent: float | None = None

    verification_passed: bool
    stdout_match: bool

    status: ExperimentStatus