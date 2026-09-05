from pydantic import BaseModel


class VerificationResult(BaseModel):
    passed: bool

    syntax_valid: bool

    baseline_return_code: int
    candidate_return_code: int

    stdout_match: bool
    stderr_match: bool

    baseline_stdout: str
    candidate_stdout: str

    baseline_stderr: str
    candidate_stderr: str

    repetitions: int
    matches: int

    reason: str