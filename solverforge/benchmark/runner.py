import statistics
import subprocess
import time
from pathlib import Path

from solverforge.benchmark.schemas import BenchmarkResult


class BenchmarkRunner:
    def __init__(
        self,
        warmup_runs: int = 1,
        trials: int = 5,
        timeout_seconds: float = 60.0,
    ) -> None:
        if warmup_runs < 0:
            raise ValueError("warmup_runs must be >= 0")

        if trials < 1:
            raise ValueError("trials must be >= 1")

        self.warmup_runs = warmup_runs
        self.trials = trials
        self.timeout_seconds = timeout_seconds

    def _run_once(
        self,
        command: list[str],
        cwd: Path | None = None,
    ) -> tuple[float, subprocess.CompletedProcess[str]]:
        start = time.perf_counter()

        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )

        end = time.perf_counter()

        runtime = end - start

        return runtime, completed

    def run(
        self,
        command: list[str],
        cwd: Path | None = None,
    ) -> BenchmarkResult:
        # Warmup runs
        for _ in range(self.warmup_runs):
            _, completed = self._run_once(
                command=command,
                cwd=cwd,
            )

            if completed.returncode != 0:
                return BenchmarkResult(
                    command=command,
                    warmup_runs=self.warmup_runs,
                    trials=self.trials,
                    runtimes_seconds=[],
                    median_seconds=0.0,
                    mean_seconds=0.0,
                    std_dev_seconds=0.0,
                    min_seconds=0.0,
                    max_seconds=0.0,
                    return_code=completed.returncode,
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                    output_consistent=False,
                    success=False,
                )

        runtimes: list[float] = []
        outputs: list[str] = []

        final_result: subprocess.CompletedProcess[str] | None = None

        for _ in range(self.trials):
            runtime, completed = self._run_once(
                command=command,
                cwd=cwd,
            )

            final_result = completed

            if completed.returncode != 0:
                return BenchmarkResult(
                    command=command,
                    warmup_runs=self.warmup_runs,
                    trials=self.trials,
                    runtimes_seconds=runtimes,
                    median_seconds=(
                        statistics.median(runtimes)
                        if runtimes
                        else 0.0
                    ),
                    mean_seconds=(
                        statistics.mean(runtimes)
                        if runtimes
                        else 0.0
                    ),
                    std_dev_seconds=(
                        statistics.pstdev(runtimes)
                        if len(runtimes) > 1
                        else 0.0
                    ),
                    min_seconds=(
                        min(runtimes)
                        if runtimes
                        else 0.0
                    ),
                    max_seconds=(
                        max(runtimes)
                        if runtimes
                        else 0.0
                    ),
                    return_code=completed.returncode,
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                    output_consistent=False,
                    success=False,
                )

            runtimes.append(runtime)
            outputs.append(completed.stdout)

        if final_result is None:
            raise RuntimeError(
                "Benchmark completed without producing a result."
            )

        output_consistent = len(set(outputs)) == 1

        success = (
            final_result.returncode == 0
            and output_consistent
        )

        return BenchmarkResult(
            command=command,
            warmup_runs=self.warmup_runs,
            trials=self.trials,
            runtimes_seconds=runtimes,
            median_seconds=statistics.median(runtimes),
            mean_seconds=statistics.mean(runtimes),
            std_dev_seconds=(
                statistics.pstdev(runtimes)
                if len(runtimes) > 1
                else 0.0
            ),
            min_seconds=min(runtimes),
            max_seconds=max(runtimes),
            return_code=final_result.returncode,
            stdout=final_result.stdout,
            stderr=final_result.stderr,
            output_consistent=output_consistent,
            success=success,
        )