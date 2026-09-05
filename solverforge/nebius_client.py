import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError

from solverforge.schemas import OptimizationAnalysis


load_dotenv()


DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"


class NebiusClient:
    def __init__(self) -> None:
        api_key = os.getenv("NEBIUS_API_KEY")

        if not api_key:
            raise RuntimeError(
                "NEBIUS_API_KEY is not set. "
                "Add it to your .env file."
            )

        self.base_url = os.getenv(
            "NEBIUS_BASE_URL",
            DEFAULT_BASE_URL,
        )

        self.model = os.getenv(
            "NEBIUS_MODEL",
            DEFAULT_MODEL,
        )

        self.client = OpenAI(
            api_key=api_key,
            base_url=self.base_url,
        )

    def analyze_code(
        self,
        source_code: str,
        filename: str,
    ) -> OptimizationAnalysis:
        schema = OptimizationAnalysis.model_json_schema()

        system_prompt = """
You are the optimization research component of SolverForge.

SolverForge experimentally improves algorithms and performance-sensitive
software.

Your job is NOT to rewrite the entire program.

Instead:

1. Analyze the supplied source code.
2. Identify likely computational bottlenecks.
3. Produce exactly three distinct optimization hypotheses.
4. Each hypothesis must describe one measurable experiment.
5. Do not claim that an optimization works before it has been benchmarked.
6. Preserve program correctness.
7. Prefer algorithmic improvements over cosmetic code changes.
8. Include tests or benchmarks that would validate each hypothesis.

Every hypothesis MUST contain all 8 fields:

1. title
2. hypothesis
3. proposed_change
4. target_files
5. expected_effect
6. risk
7. validation_steps
8. confidence

Never omit confidence.

confidence must always be exactly one of:

"low"
"medium"
"high"

Your entire response must be ONE JSON object.

The root object must contain:

- summary
- suspected_bottleneck
- hypotheses

The hypotheses array must contain exactly three objects.

Do not return Markdown.
Do not return code fences.
Do not return a JSON array as the root.

You are generating hypotheses only.

Another SolverForge component will implement and experimentally test them.
""".strip()

        user_prompt = f"""
Analyze this Python source file for potential performance optimizations.

Filename:
{filename}

SOURCE CODE START

{source_code}

SOURCE CODE END

Produce exactly three distinct optimization hypotheses.

Remember:

- Return one JSON object.
- Include summary.
- Include suspected_bottleneck.
- Include exactly three hypotheses.
- Every hypothesis must include confidence.
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
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "optimization_analysis",
                    "schema": schema,
                },
            },
            temperature=0.1,
        )

        message = response.choices[0].message

        if getattr(message, "refusal", None):
            raise RuntimeError(
                f"Model refused request: {message.refusal}"
            )

        if not message.content:
            raise RuntimeError(
                "Nemotron returned an empty response."
            )

        try:
            raw_data = json.loads(message.content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Nemotron returned invalid JSON."
            ) from exc

        try:
            return OptimizationAnalysis.model_validate(
                raw_data
            )

        except ValidationError as exc:
            print()
            print(
                "Nemotron response failed schema validation."
            )
            print(
                "Attempting automatic repair..."
            )
            print()

            return self._repair_analysis(
                raw_data=raw_data,
                validation_error=str(exc),
            )

    def _repair_analysis(
        self,
        raw_data: object,
        validation_error: str,
    ) -> OptimizationAnalysis:
        schema = OptimizationAnalysis.model_json_schema()

        repair_system_prompt = """
You repair structured JSON responses.

Your job is to fix the supplied JSON so that it exactly satisfies the
required OptimizationAnalysis schema.

Do not change the meaning unnecessarily.

Return only valid JSON.

Do not return Markdown.
Do not return code fences.
Do not provide an explanation.
""".strip()

        repair_user_prompt = f"""
The previous OptimizationAnalysis response failed validation.

VALIDATION ERROR:

{validation_error}

PREVIOUS JSON:

{json.dumps(raw_data, indent=2)}

Repair the JSON so that it exactly satisfies the required schema.

The root object must contain:

- summary
- suspected_bottleneck
- hypotheses

hypotheses must contain exactly three objects.

Every hypothesis MUST contain all of these fields:

- title
- hypothesis
- proposed_change
- target_files
- expected_effect
- risk
- validation_steps
- confidence

confidence MUST be exactly one of:

- low
- medium
- high

Return one corrected JSON object only.
""".strip()

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": repair_system_prompt,
                },
                {
                    "role": "user",
                    "content": repair_user_prompt,
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "optimization_analysis",
                    "schema": schema,
                },
            },
            temperature=0.0,
        )

        message = response.choices[0].message

        if getattr(message, "refusal", None):
            raise RuntimeError(
                f"Model refused repair request: "
                f"{message.refusal}"
            )

        if not message.content:
            raise RuntimeError(
                "Nemotron returned an empty repair response."
            )

        try:
            repaired_data = json.loads(
                message.content
            )
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Nemotron returned invalid JSON "
                "during schema repair."
            ) from exc

        try:
            return OptimizationAnalysis.model_validate(
                repaired_data
            )

        except ValidationError as exc:
            raise RuntimeError(
                "Nemotron response still failed schema "
                "validation after one repair attempt.\n\n"
                f"{exc}"
            ) from exc