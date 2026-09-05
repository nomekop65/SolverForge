import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from solverforge.benchmark.paired_runner import (
    PairedBenchmarkRunner,
)
from solverforge.benchmark.runner import BenchmarkRunner
from solverforge.engineering.engineer import EngineerAgent
from solverforge.experiments import create_experiment_directory
from solverforge.history.repository import ExperimentRepository
from solverforge.history.schemas import ExperimentRecord
from solverforge.nebius_client import NebiusClient
from solverforge.schemas import OptimizationHypothesis
from solverforge.verification.verifier import CorrectnessVerifier


MIN_SPEEDUP = 1.10
MAX_GENERATIONS = 3


def print_benchmark(
    title: str,
    benchmark,
) -> None:
    print(title)
    print("=" * 80)

    print(
        f"Warmups:           "
        f"{benchmark.warmup_runs}"
    )

    print(
        f"Trials:            "
        f"{benchmark.trials}"
    )

    print(
        f"Median:            "
        f"{benchmark.median_seconds:.6f} s"
    )

    print(
        f"Mean:              "
        f"{benchmark.mean_seconds:.6f} s"
    )

    print(
        f"Std dev:           "
        f"{benchmark.std_dev_seconds:.6f} s"
    )

    print(
        f"Min:               "
        f"{benchmark.min_seconds:.6f} s"
    )

    print(
        f"Max:               "
        f"{benchmark.max_seconds:.6f} s"
    )

    print(
        f"Output consistent: "
        f"{benchmark.output_consistent}"
    )

    print()


def print_recent_experiments(
    repository: ExperimentRepository,
) -> None:
    experiments = repository.list_recent(
        limit=15
    )

    if not experiments:
        return

    print()
    print("Recent experiment history")
    print("=" * 100)

    print(
        f"{'ID':<10}"
        f"{'Parent':<10}"
        f"{'Status':<22}"
        f"{'Speedup':<12}"
        f"Hypothesis"
    )

    print("-" * 100)

    for experiment in experiments:
        speedup_text = "-"

        if experiment.speedup is not None:
            speedup_text = (
                f"{experiment.speedup:.3f}x"
            )

        parent_text = "-"

        if experiment.parent_id:
            parent_text = (
                experiment.parent_id[:8]
            )

        print(
            f"{experiment.experiment_id[:8]:<10}"
            f"{parent_text:<10}"
            f"{experiment.status:<22}"
            f"{speedup_text:<12}"
            f"{experiment.hypothesis_title}"
        )

    print()


def create_record(
    *,
    experiment_id: str,
    timestamp: str,
    parent_id: str | None,
    source_path: Path,
    candidate_path: Path,
    hypothesis: OptimizationHypothesis,
    baseline_median: float,
    candidate_median: float | None,
    speedup: float | None,
    runtime_change_percent: float | None,
    verification_passed: bool,
    stdout_match: bool,
    status: str,
) -> ExperimentRecord:
    return ExperimentRecord(
        experiment_id=experiment_id,
        timestamp=timestamp,
        parent_id=parent_id,
        source_file=str(source_path),
        candidate_file=str(candidate_path),
        hypothesis_title=hypothesis.title,
        hypothesis=hypothesis.hypothesis,
        proposed_change=hypothesis.proposed_change,
        confidence=hypothesis.confidence,
        baseline_median=baseline_median,
        candidate_median=candidate_median,
        speedup=speedup,
        runtime_change_percent=(
            runtime_change_percent
        ),
        verification_passed=(
            verification_passed
        ),
        stdout_match=stdout_match,
        status=status,
    )


def run_experiment(
    *,
    generation: int,
    experiment_number: int,
    hypothesis: OptimizationHypothesis,
    source_path: Path,
    source_code: str,
    parent_id: str | None,
    baseline_command: list[str],
    baseline_median: float,
    engineer: EngineerAgent,
    verifier: CorrectnessVerifier,
    paired_benchmark_runner: PairedBenchmarkRunner,
    repository: ExperimentRepository,
) -> ExperimentRecord:
    experiment_id = str(
        uuid4()
    )

    timestamp = (
        datetime.now()
        .astimezone()
        .isoformat()
    )

    print()
    print("=" * 100)
    print(
        f"GENERATION {generation} "
        f"- EXPERIMENT {experiment_number}"
    )
    print("=" * 100)

    print()
    print(
        f"Title: "
        f"{hypothesis.title}"
    )

    print()
    print("Hypothesis:")
    print(
        hypothesis.hypothesis
    )

    print()
    print("Proposed change:")
    print(
        hypothesis.proposed_change
    )

    print()
    print(
        f"Confidence: "
        f"{hypothesis.confidence}"
    )

    print(
        f"Experiment ID: "
        f"{experiment_id}"
    )

    print(
        f"Parent ID:     "
        f"{parent_id or '-'}"
    )

    # ---------------------------------------------------------
    # Generate candidate
    # ---------------------------------------------------------

    print()
    print("Generating candidate...")

    candidate_source = (
        engineer.generate_candidate(
            source_code=source_code,
            filename=str(source_path),
            hypothesis=hypothesis,
        )
    )

    experiment_dir = (
        create_experiment_directory()
    )

    candidate_path = (
        experiment_dir
        / "candidate.py"
    )

    candidate_path.write_text(
        candidate_source,
        encoding="utf-8",
    )

    print(
        f"Candidate: "
        f"{candidate_path}"
    )

    candidate_command = [
        sys.executable,
        str(candidate_path),
    ]

    # ---------------------------------------------------------
    # Stronger correctness verification
    # ---------------------------------------------------------

    print()
    print("Verifying correctness...")

    verification = verifier.verify(
        baseline_command=baseline_command,
        candidate_command=candidate_command,
    )

    print(
        f"Syntax valid: "
        f"{verification.syntax_valid}"
    )

    print(
        f"Passed: "
        f"{verification.passed}"
    )

    print(
        f"Matches: "
        f"{verification.matches}/"
        f"{verification.repetitions}"
    )

    print(
        f"Reason: "
        f"{verification.reason}"
    )

    if not verification.passed:
        record = create_record(
            experiment_id=experiment_id,
            timestamp=timestamp,
            parent_id=parent_id,
            source_path=source_path,
            candidate_path=candidate_path,
            hypothesis=hypothesis,
            baseline_median=baseline_median,
            candidate_median=None,
            speedup=None,
            runtime_change_percent=None,
            verification_passed=False,
            stdout_match=(
                verification.stdout_match
            ),
            status="FAILED_VERIFICATION",
        )

        repository.save(record)

        print()
        print(
            "Decision: "
            "FAILED_VERIFICATION"
        )

        if verification.candidate_stderr:
            print()
            print("Candidate stderr")
            print("-" * 80)
            print(
                verification.candidate_stderr
            )

        if (
            verification.syntax_valid
            and not verification.stdout_match
        ):
            print()
            print("Baseline stdout")
            print("-" * 80)
            print(
                verification.baseline_stdout.strip()
            )

            print()
            print("Candidate stdout")
            print("-" * 80)
            print(
                verification.candidate_stdout.strip()
            )

        return record

    # ---------------------------------------------------------
    # Paired/interleaved benchmark
    # ---------------------------------------------------------

    print()
    print(
        "Correctness verified."
    )

    print(
        "Running paired benchmark..."
    )

    paired_result = (
        paired_benchmark_runner.run(
            baseline_command=(
                baseline_command
            ),
            candidate_command=(
                candidate_command
            ),
        )
    )

    if not paired_result.success:
        record = create_record(
            experiment_id=experiment_id,
            timestamp=timestamp,
            parent_id=parent_id,
            source_path=source_path,
            candidate_path=candidate_path,
            hypothesis=hypothesis,
            baseline_median=baseline_median,
            candidate_median=None,
            speedup=None,
            runtime_change_percent=None,
            verification_passed=True,
            stdout_match=True,
            status="FAILED_BENCHMARK",
        )

        repository.save(record)

        print()
        print(
            "Decision: "
            "FAILED_BENCHMARK"
        )

        return record

    paired_baseline_median = (
        paired_result.baseline_median
    )

    candidate_median = (
        paired_result.candidate_median
    )

    speedup = (
        paired_result.median_speedup
    )

    if paired_baseline_median <= 0:
        raise RuntimeError(
            "Paired baseline median "
            "must be greater than zero."
        )

    if candidate_median <= 0:
        raise RuntimeError(
            "Candidate median must "
            "be greater than zero."
        )

    runtime_change_percent = (
        (
            candidate_median
            / paired_baseline_median
        )
        - 1.0
    ) * 100.0

    print()
    print("Paired benchmark")
    print("-" * 80)

    print(
        f"Warmups:             "
        f"{paired_result.warmup_runs}"
    )

    print(
        f"Trials:              "
        f"{paired_result.trials}"
    )

    print(
        f"Baseline median:     "
        f"{paired_baseline_median:.6f} s"
    )

    print(
        f"Candidate median:    "
        f"{candidate_median:.6f} s"
    )

    print(
        f"Median speedup:      "
        f"{speedup:.3f}x"
    )

    print(
        f"Worst trial speedup: "
        f"{paired_result.min_speedup:.3f}x"
    )

    print(
        f"Best trial speedup:  "
        f"{paired_result.max_speedup:.3f}x"
    )

    print(
        f"Runtime change:      "
        f"{runtime_change_percent:+.2f}%"
    )

    print(
        f"Threshold:           "
        f"{MIN_SPEEDUP:.2f}x"
    )

    # ---------------------------------------------------------
    # Accept/reject
    # ---------------------------------------------------------

    if speedup >= MIN_SPEEDUP:
        status = "ACCEPTED"
    else:
        status = "REJECTED"

    print(
        f"Decision:            "
        f"{status}"
    )

    record = create_record(
        experiment_id=experiment_id,
        timestamp=timestamp,
        parent_id=parent_id,
        source_path=source_path,
        candidate_path=candidate_path,
        hypothesis=hypothesis,
        baseline_median=(
            paired_baseline_median
        ),
        candidate_median=(
            candidate_median
        ),
        speedup=speedup,
        runtime_change_percent=(
            runtime_change_percent
        ),
        verification_passed=True,
        stdout_match=True,
        status=status,
    )

    repository.save(record)

    print(
        "Experiment saved."
    )

    return record


def print_generation_summary(
    generation: int,
    experiments: list[ExperimentRecord],
) -> None:
    print()
    print("=" * 100)

    print(
        f"GENERATION {generation} SUMMARY"
    )

    print("=" * 100)

    print()

    print(
        f"{'#':<4}"
        f"{'Status':<22}"
        f"{'Speedup':<12}"
        f"{'Runtime':<14}"
        f"Hypothesis"
    )

    print("-" * 100)

    for index, experiment in enumerate(
        experiments,
        start=1,
    ):
        speedup = "-"

        if experiment.speedup is not None:
            speedup = (
                f"{experiment.speedup:.3f}x"
            )

        runtime = "-"

        if (
            experiment.candidate_median
            is not None
        ):
            runtime = (
                f"{experiment.candidate_median:.6f}s"
            )

        print(
            f"{index:<4}"
            f"{experiment.status:<22}"
            f"{speedup:<12}"
            f"{runtime:<14}"
            f"{experiment.hypothesis_title}"
        )

    print()


def find_best_accepted(
    experiments: list[ExperimentRecord],
) -> ExperimentRecord | None:
    accepted = [
        experiment
        for experiment in experiments
        if (
            experiment.status
            == "ACCEPTED"
            and experiment.speedup
            is not None
            and experiment.candidate_median
            is not None
        )
    ]

    if not accepted:
        return None

    return max(
        accepted,
        key=lambda experiment: (
            experiment.speedup or 0.0
        ),
    )


def main() -> None:
    # ---------------------------------------------------------
    # Original baseline
    # ---------------------------------------------------------

    original_source_path = Path(
        "examples/toy_solver.py"
    )

    if not original_source_path.exists():
        raise FileNotFoundError(
            f"Could not find baseline: "
            f"{original_source_path}"
        )

    # ---------------------------------------------------------
    # Components
    # ---------------------------------------------------------

    repository = (
        ExperimentRepository()
    )

    # Used for generation-level baseline reporting.
    benchmark_runner = BenchmarkRunner(
        warmup_runs=1,
        trials=5,
        timeout_seconds=60.0,
    )

    # Stronger correctness checking.
    verifier = CorrectnessVerifier(
        timeout_seconds=60.0,
        repetitions=3,
    )

    # Stronger candidate-vs-baseline measurement.
    paired_benchmark_runner = (
        PairedBenchmarkRunner(
            warmup_runs=2,
            trials=9,
            timeout_seconds=60.0,
        )
    )

    engineer = EngineerAgent()
    analyzer = NebiusClient()

    # ---------------------------------------------------------
    # Current optimization state
    # ---------------------------------------------------------

    current_source_path = (
        original_source_path
    )

    current_parent_id: str | None = (
        None
    )

    original_baseline_median: (
        float | None
    ) = None

    lineage: list[
        ExperimentRecord
    ] = []

    print()
    print("SolverForge")
    print("=" * 100)

    print(
        f"Original target: "
        f"{original_source_path}"
    )

    print(
        f"Maximum generations: "
        f"{MAX_GENERATIONS}"
    )

    print(
        f"Minimum speedup: "
        f"{MIN_SPEEDUP:.2f}x"
    )

    print(
        "Correctness repetitions: "
        f"{verifier.repetitions}"
    )

    print(
        "Paired benchmark trials: "
        f"{paired_benchmark_runner.trials}"
    )

    # =========================================================
    # ITERATIVE OPTIMIZATION LOOP
    # =========================================================

    for generation in range(
        1,
        MAX_GENERATIONS + 1,
    ):
        print()
        print()
        print("#" * 100)

        print(
            f"GENERATION {generation}"
        )

        print("#" * 100)

        print()
        print(
            f"Current baseline file: "
            f"{current_source_path}"
        )

        print(
            f"Current parent ID: "
            f"{current_parent_id or '-'}"
        )

        current_source_code = (
            current_source_path.read_text(
                encoding="utf-8"
            )
        )

        current_baseline_command = [
            sys.executable,
            str(current_source_path),
        ]

        # -----------------------------------------------------
        # Baseline benchmark
        # -----------------------------------------------------

        print()

        baseline_benchmark = (
            benchmark_runner.run(
                command=(
                    current_baseline_command
                ),
            )
        )

        if not baseline_benchmark.success:
            if baseline_benchmark.stderr:
                print(
                    baseline_benchmark.stderr
                )

            raise RuntimeError(
                "Current baseline failed."
            )

        print_benchmark(
            title=(
                f"Generation {generation} "
                "baseline benchmark"
            ),
            benchmark=baseline_benchmark,
        )

        baseline_median = (
            baseline_benchmark.median_seconds
        )

        if baseline_median <= 0:
            raise RuntimeError(
                "Baseline median must "
                "be greater than zero."
            )

        if original_baseline_median is None:
            original_baseline_median = (
                baseline_median
            )

        # -----------------------------------------------------
        # Nemotron analyzes current winner
        # -----------------------------------------------------

        print(
            f"Analyzing generation "
            f"{generation} baseline..."
        )

        analysis = analyzer.analyze_code(
            source_code=(
                current_source_code
            ),
            filename=str(
                current_source_path
            ),
        )

        print()
        print("Analysis")
        print("-" * 80)

        print(
            analysis.summary
        )

        print()
        print("Suspected bottleneck")
        print("-" * 80)

        print(
            analysis.suspected_bottleneck
        )

        print()
        print(
            f"Generated "
            f"{len(analysis.hypotheses)} "
            f"hypotheses."
        )

        # -----------------------------------------------------
        # Run all hypotheses
        # -----------------------------------------------------

        generation_results: list[
            ExperimentRecord
        ] = []

        for (
            experiment_number,
            hypothesis,
        ) in enumerate(
            analysis.hypotheses,
            start=1,
        ):
            try:
                result = run_experiment(
                    generation=generation,
                    experiment_number=(
                        experiment_number
                    ),
                    hypothesis=hypothesis,
                    source_path=(
                        current_source_path
                    ),
                    source_code=(
                        current_source_code
                    ),
                    parent_id=(
                        current_parent_id
                    ),
                    baseline_command=(
                        current_baseline_command
                    ),
                    baseline_median=(
                        baseline_median
                    ),
                    engineer=engineer,
                    verifier=verifier,
                    paired_benchmark_runner=(
                        paired_benchmark_runner
                    ),
                    repository=repository,
                )

                generation_results.append(
                    result
                )

            except Exception as exc:
                print()
                print(
                    f"Experiment "
                    f"{experiment_number} "
                    f"failed unexpectedly."
                )

                print(
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

                print(
                    "Continuing with remaining "
                    "experiments."
                )

        # -----------------------------------------------------
        # Generation summary
        # -----------------------------------------------------

        print_generation_summary(
            generation=generation,
            experiments=(
                generation_results
            ),
        )

        # -----------------------------------------------------
        # Select best accepted child
        # -----------------------------------------------------

        best = find_best_accepted(
            generation_results
        )

        if best is None:
            print("=" * 100)

            print(
                f"Generation {generation}: "
                "no candidate achieved "
                f"{MIN_SPEEDUP:.2f}x."
            )

            print(
                "Optimization converged."
            )

            print("=" * 100)

            break

        # -----------------------------------------------------
        # Promote winner
        # -----------------------------------------------------

        print("=" * 100)

        print(
            f"GENERATION {generation} WINNER"
        )

        print("=" * 100)

        print(
            f"Experiment: "
            f"{best.experiment_id}"
        )

        print(
            f"Hypothesis: "
            f"{best.hypothesis_title}"
        )

        print(
            f"Speedup:    "
            f"{best.speedup:.3f}x"
        )

        print(
            f"Old runtime: "
            f"{best.baseline_median:.6f} s"
        )

        print(
            f"New runtime: "
            f"{best.candidate_median:.6f} s"
        )

        print(
            f"New baseline: "
            f"{best.candidate_file}"
        )

        lineage.append(
            best
        )

        current_parent_id = (
            best.experiment_id
        )

        current_source_path = Path(
            best.candidate_file
        )

    # =========================================================
    # FINAL RESULT
    # =========================================================

    print()
    print()
    print("#" * 100)

    print(
        "FINAL OPTIMIZATION RESULT"
    )

    print("#" * 100)
    print()

    if not lineage:
        print(
            "No accepted optimization "
            "was found."
        )

        print(
            f"Final file: "
            f"{original_source_path}"
        )

    else:
        print(
            f"Accepted generations: "
            f"{len(lineage)}"
        )

        print()
        print("Optimization lineage")
        print("-" * 100)

        for (
            generation,
            experiment,
        ) in enumerate(
            lineage,
            start=1,
        ):
            print(
                f"Generation {generation}: "
                f"{experiment.experiment_id[:8]} "
                f"| "
                f"{experiment.speedup:.3f}x "
                f"| "
                f"{experiment.hypothesis_title}"
            )

        final_winner = (
            lineage[-1]
        )

        final_runtime = (
            final_winner.candidate_median
        )

        print()
        print("Final winner")
        print("=" * 100)

        print(
            f"Experiment: "
            f"{final_winner.experiment_id}"
        )

        print(
            f"File: "
            f"{final_winner.candidate_file}"
        )

        print(
            f"Runtime: "
            f"{final_runtime:.6f} s"
        )

        if (
            original_baseline_median
            is not None
            and final_runtime is not None
            and final_runtime > 0
        ):
            total_speedup = (
                original_baseline_median
                / final_runtime
            )

            total_runtime_change = (
                (
                    final_runtime
                    / original_baseline_median
                )
                - 1.0
            ) * 100.0

            print(
                f"Original runtime: "
                f"{original_baseline_median:.6f} s"
            )

            print(
                f"Total speedup: "
                f"{total_speedup:.3f}x"
            )

            print(
                f"Total runtime change: "
                f"{total_runtime_change:+.2f}%"
            )

    print_recent_experiments(
        repository
    )


if __name__ == "__main__":
    main()