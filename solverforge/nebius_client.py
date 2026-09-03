import json
import os

from dotenv import load_dotenv
from openai import OpenAI

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

    Analyze performance-sensitive source code and generate optimization experiments.

    IMPORTANT:
    Your entire response must be ONE JSON OBJECT.

    The root JSON object must contain exactly these keys:

    {
        "summary": "string",
        "suspected_bottleneck": "string",
        "hypotheses": [
            {
                "title": "string",
                "hypothesis": "string",
                "proposed_change": "string",
                "target_files": ["string"],
                "expected_effect": "string",
                "risk": "string",
                "validation_steps": ["string"],
                "confidence": "low | medium | high"
            }
        ]
    }

    Requirements:

    1. "hypotheses" must contain exactly 3 items.
    2. Do NOT return a JSON array as the root.
    3. Do NOT return Markdown.
    4. Do NOT return code fences.
    5. Do NOT rewrite the program.
    6. Each hypothesis must describe one measurable optimization experiment.
    7. Preserve correctness.
    8. Do not claim an optimization succeeded before benchmarking.
    9. Prefer algorithmic performance improvements over cosmetic changes.
    """.strip()

        user_prompt = f"""
    Analyze the following Python source file.

    Filename:
    {filename}

    SOURCE CODE START
    {source_code}
    SOURCE CODE END

    Return one OptimizationAnalysis JSON object containing:

    - summary
    - suspected_bottleneck
    - exactly three hypotheses
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

        raw_data = json.loads(message.content)

        return OptimizationAnalysis.model_validate(raw_data)