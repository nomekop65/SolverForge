import statistics
import subprocess
import time
from pathlib import Path

from solverforge.benchmark.paired_schemas import (
    PairedBenchmarkResult,
)


class PairedBenchmarkRunner:
    def __init__(
        self,
        warmup_runs: int = 2,
        trials: int = 9,
        timeout_seconds: float = 60.0,
    ) -> None:
        if warmup_runs < 0:
            raise ValueError(
                "warmup_runs must be >= 0"
            )

        if trials < 3:
            raise ValueError(
                "trials must be >= 3"
            )

        self.warmup_runs = warmup_runs
        self.trials = trials
        self.timeout_seconds = timeout_seconds

    def _run_once(
        self,
        command: list[str],
        cwd: Path | None = None,
    ) -> tuple[
        float,
        subprocess.CompletedProcess[str],
    ]:
        start = time.perf_counter()

        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )

        elapsed = (
            time.perf_counter()
            - start
        )

        return elapsed, result

    def run(
        self,
        baseline_command: list[str],
        candidate_command: list[str],
        cwd: Path | None = None,
    ) -> PairedBenchmarkResult:
        # -----------------------------------------------------
        # Warmup
        # -----------------------------------------------------

        for _ in range(self.warmup_runs):
            _, baseline = self._run_once(
                baseline_command,
                cwd=cwd,
            )

            _, candidate = self._run_once(
                candidate_command,
                cwd=cwd,
            )

            if (
                baseline.returncode != 0
                or candidate.returncode != 0
            ):
                return PairedBenchmarkResult(
                    trials=self.trials,
                    warmup_runs=self.warmup_runs,
                    baseline_runtimes=[],
                    candidate_runtimes=[],
                    trial_speedups=[],
                    baseline_median=0.0,
                    candidate_median=0.0,
                    median_speedup=0.0,
                    min_speedup=0.0,
                    max_speedup=0.0,
                    baseline_output_consistent=False,
                    candidate_output_consistent=False,
                    success=False,
                )

        baseline_runtimes: list[float] = []
        candidate_runtimes: list[float] = []

        baseline_outputs: list[str] = []
        candidate_outputs: list[str] = []

        # -----------------------------------------------------
        # Interleaved trials
        # -----------------------------------------------------

        for trial in range(self.trials):
            if trial % 2 == 0:
                baseline_time, baseline = (
                    self._run_once(
                        baseline_command,
                        cwd=cwd,
                    )
                )

                candidate_time, candidate = (
                    self._run_once(
                        candidate_command,
                        cwd=cwd,
                    )
                )

            else:
                candidate_time, candidate = (
                    self._run_once(
                        candidate_command,
                        cwd=cwd,
                    )
                )

                baseline_time, baseline = (
                    self._run_once(
                        baseline_command,
                        cwd=cwd,
                    )
                )

            if (
                baseline.returncode != 0
                or candidate.returncode != 0
            ):
                return PairedBenchmarkResult(
                    trials=self.trials,
                    warmup_runs=self.warmup_runs,
                    baseline_runtimes=(
                        baseline_runtimes
                    ),
                    candidate_runtimes=(
                        candidate_runtimes
                    ),
                    trial_speedups=[],
                    baseline_median=0.0,
                    candidate_median=0.0,
                    median_speedup=0.0,
                    min_speedup=0.0,
                    max_speedup=0.0,
                    baseline_output_consistent=False,
                    candidate_output_consistent=False,
                    success=False,
                )

            baseline_runtimes.append(
                baseline_time
            )

            candidate_runtimes.append(
                candidate_time
            )

            baseline_outputs.append(
                baseline.stdout
            )

            candidate_outputs.append(
                candidate.stdout
            )

        # -----------------------------------------------------
        # Calculate paired speedups
        # -----------------------------------------------------

        trial_speedups = [
            baseline_time
            / candidate_time
            for baseline_time, candidate_time
            in zip(
                baseline_runtimes,
                candidate_runtimes,
                strict=True,
            )
        ]

        baseline_consistent = (
            len(set(baseline_outputs)) == 1
        )

        candidate_consistent = (
            len(set(candidate_outputs)) == 1
        )

        return PairedBenchmarkResult(
            trials=self.trials,
            warmup_runs=self.warmup_runs,
            baseline_runtimes=(
                baseline_runtimes
            ),
            candidate_runtimes=(
                candidate_runtimes
            ),
            trial_speedups=trial_speedups,
            baseline_median=statistics.median(
                baseline_runtimes
            ),
            candidate_median=statistics.median(
                candidate_runtimes
            ),
            median_speedup=statistics.median(
                trial_speedups
            ),
            min_speedup=min(
                trial_speedups
            ),
            max_speedup=max(
                trial_speedups
            ),
            baseline_output_consistent=(
                baseline_consistent
            ),
            candidate_output_consistent=(
                candidate_consistent
            ),
            success=(
                baseline_consistent
                and candidate_consistent
            ),
        )