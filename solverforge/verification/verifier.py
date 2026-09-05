import py_compile
import subprocess
from pathlib import Path

from solverforge.verification.schemas import VerificationResult


class CorrectnessVerifier:
    def __init__(
        self,
        timeout_seconds: float = 60.0,
        repetitions: int = 3,
    ) -> None:
        if repetitions < 1:
            raise ValueError(
                "repetitions must be >= 1"
            )

        self.timeout_seconds = timeout_seconds
        self.repetitions = repetitions

    def _run(
        self,
        command: list[str],
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )

    def _compile_candidate(
        self,
        candidate_command: list[str],
    ) -> tuple[bool, str]:
        if len(candidate_command) < 2:
            return True, ""

        candidate_path = Path(
            candidate_command[1]
        )

        if candidate_path.suffix != ".py":
            return True, ""

        try:
            py_compile.compile(
                str(candidate_path),
                doraise=True,
            )

            return True, ""

        except py_compile.PyCompileError as exc:
            return False, str(exc)

    def verify(
        self,
        baseline_command: list[str],
        candidate_command: list[str],
        cwd: Path | None = None,
    ) -> VerificationResult:
        syntax_valid, compile_error = (
            self._compile_candidate(
                candidate_command
            )
        )

        if not syntax_valid:
            return VerificationResult(
                passed=False,
                syntax_valid=False,
                baseline_return_code=0,
                candidate_return_code=1,
                stdout_match=False,
                stderr_match=False,
                baseline_stdout="",
                candidate_stdout="",
                baseline_stderr="",
                candidate_stderr=compile_error,
                repetitions=self.repetitions,
                matches=0,
                reason=(
                    "Candidate failed Python "
                    "syntax compilation."
                ),
            )

        matches = 0

        last_baseline = None
        last_candidate = None

        stdout_match = True
        stderr_match = True

        for _ in range(self.repetitions):
            baseline = self._run(
                command=baseline_command,
                cwd=cwd,
            )

            candidate = self._run(
                command=candidate_command,
                cwd=cwd,
            )

            last_baseline = baseline
            last_candidate = candidate

            if baseline.returncode != 0:
                return VerificationResult(
                    passed=False,
                    syntax_valid=True,
                    baseline_return_code=(
                        baseline.returncode
                    ),
                    candidate_return_code=(
                        candidate.returncode
                    ),
                    stdout_match=False,
                    stderr_match=False,
                    baseline_stdout=(
                        baseline.stdout
                    ),
                    candidate_stdout=(
                        candidate.stdout
                    ),
                    baseline_stderr=(
                        baseline.stderr
                    ),
                    candidate_stderr=(
                        candidate.stderr
                    ),
                    repetitions=self.repetitions,
                    matches=matches,
                    reason=(
                        "Baseline execution failed."
                    ),
                )

            if candidate.returncode != 0:
                return VerificationResult(
                    passed=False,
                    syntax_valid=True,
                    baseline_return_code=(
                        baseline.returncode
                    ),
                    candidate_return_code=(
                        candidate.returncode
                    ),
                    stdout_match=False,
                    stderr_match=False,
                    baseline_stdout=(
                        baseline.stdout
                    ),
                    candidate_stdout=(
                        candidate.stdout
                    ),
                    baseline_stderr=(
                        baseline.stderr
                    ),
                    candidate_stderr=(
                        candidate.stderr
                    ),
                    repetitions=self.repetitions,
                    matches=matches,
                    reason=(
                        "Candidate execution failed."
                    ),
                )

            current_stdout_match = (
                baseline.stdout
                == candidate.stdout
            )

            current_stderr_match = (
                baseline.stderr
                == candidate.stderr
            )

            stdout_match = (
                stdout_match
                and current_stdout_match
            )

            stderr_match = (
                stderr_match
                and current_stderr_match
            )

            if current_stdout_match:
                matches += 1

        if last_baseline is None:
            raise RuntimeError(
                "Verification did not execute."
            )

        if last_candidate is None:
            raise RuntimeError(
                "Verification did not execute."
            )

        passed = (
            syntax_valid
            and matches == self.repetitions
        )

        if passed:
            reason = (
                "Candidate matched baseline "
                f"for all {self.repetitions} runs."
            )
        else:
            reason = (
                "Candidate behavior differed "
                "from baseline."
            )

        return VerificationResult(
            passed=passed,
            syntax_valid=syntax_valid,
            baseline_return_code=(
                last_baseline.returncode
            ),
            candidate_return_code=(
                last_candidate.returncode
            ),
            stdout_match=stdout_match,
            stderr_match=stderr_match,
            baseline_stdout=(
                last_baseline.stdout
            ),
            candidate_stdout=(
                last_candidate.stdout
            ),
            baseline_stderr=(
                last_baseline.stderr
            ),
            candidate_stderr=(
                last_candidate.stderr
            ),
            repetitions=self.repetitions,
            matches=matches,
            reason=reason,
        )