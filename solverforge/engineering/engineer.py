import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from solverforge.schemas import OptimizationHypothesis


load_dotenv()


DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"


class EngineerAgent:
    def __init__(self) -> None:
        api_key = os.getenv("NEBIUS_API_KEY")

        if not api_key:
            raise RuntimeError(
                "NEBIUS_API_KEY is not set."
            )

        self.client = OpenAI(
            api_key=api_key,
            base_url=os.getenv(
                "NEBIUS_BASE_URL",
                DEFAULT_BASE_URL,
            ),
        )

        self.model = os.getenv(
            "NEBIUS_MODEL",
            DEFAULT_MODEL,
        )

    def generate_candidate(
        self,
        source_code: str,
        filename: str,
        hypothesis: OptimizationHypothesis,
    ) -> str:
        system_prompt = """
You are the implementation engineer for SolverForge.

Your job is to implement exactly ONE optimization hypothesis.

Rules:

1. Preserve the program's observable behavior.
2. Implement only the supplied optimization hypothesis.
3. Do not make unrelated refactors.
4. Do not remove required functionality.
5. Return the COMPLETE updated source file.
6. Return Python source code only.
7. Do not return Markdown.
8. Do not use code fences.
9. The generated file must be directly executable.
10. Do not claim the optimization is faster. Another system will benchmark it.

Correctness is more important than performance.
""".strip()

        user_prompt = f"""
Implement this optimization experiment.

Filename:
{filename}

OPTIMIZATION TITLE:
{hypothesis.title}

HYPOTHESIS:
{hypothesis.hypothesis}

PROPOSED CHANGE:
{hypothesis.proposed_change}

EXPECTED EFFECT:
{hypothesis.expected_effect}

RISK:
{hypothesis.risk}

SOURCE CODE START

{source_code}

SOURCE CODE END

Return the complete modified Python source file only.
""".strip()

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0.1,
        )

        message = response.choices[0].message

        if not message.content:
            raise RuntimeError(
                "EngineerAgent returned empty source code."
            )

        candidate = message.content.strip()

        candidate = self._strip_code_fence(
            candidate
        )

        return candidate

    @staticmethod
    def _strip_code_fence(
        source: str,
    ) -> str:
        if not source.startswith("```"):
            return source

        lines = source.splitlines()

        if lines:
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        return "\n".join(lines).strip()