from typing import Literal

from pydantic import BaseModel, Field


class OptimizationHypothesis(BaseModel):
    title: str = Field(
        description="Short descriptive name for the optimization."
    )

    hypothesis: str = Field(
        description=(
            "Explanation of the suspected performance problem "
            "and why the optimization may improve it."
        )
    )

    proposed_change: str = Field(
        description="Concrete code or algorithm change to test."
    )

    target_files: list[str] = Field(
        description="Files likely to require modification."
    )

    expected_effect: str = Field(
        description="Expected performance effect."
    )

    risk: str = Field(
        description="Potential correctness or performance risk."
    )

    validation_steps: list[str] = Field(
        description="Tests and benchmarks needed to validate the hypothesis."
    )

    confidence: Literal["low", "medium", "high"]


class OptimizationAnalysis(BaseModel):
    summary: str = Field(
        description="Short analysis of the current implementation."
    )

    suspected_bottleneck: str = Field(
        description="Most likely performance bottleneck."
    )

    hypotheses: list[OptimizationHypothesis] = Field(
        min_length=3,
        max_length=3,
        description="Exactly three optimization hypotheses."
    )