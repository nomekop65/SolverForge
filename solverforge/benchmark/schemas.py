from pydantic import BaseModel, Field


class BenchmarkResult(BaseModel):
    command: list[str]

    warmup_runs: int = Field(
        ge=0,
        description="Number of untimed warmup runs.",
    )

    trials: int = Field(
        ge=1,
        description="Number of timed benchmark trials.",
    )

    runtimes_seconds: list[float]

    median_seconds: float
    mean_seconds: float
    std_dev_seconds: float
    min_seconds: float
    max_seconds: float

    return_code: int
    stdout: str
    stderr: str

    output_consistent: bool

    success: bool