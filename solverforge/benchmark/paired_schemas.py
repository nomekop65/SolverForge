from pydantic import BaseModel


class PairedBenchmarkResult(BaseModel):
    trials: int
    warmup_runs: int

    baseline_runtimes: list[float]
    candidate_runtimes: list[float]

    trial_speedups: list[float]

    baseline_median: float
    candidate_median: float

    median_speedup: float

    min_speedup: float
    max_speedup: float

    baseline_output_consistent: bool
    candidate_output_consistent: bool

    success: bool