from pathlib import Path

from solverforge.nebius_client import NebiusClient


def main() -> None:
    source_path = Path("examples/toy_solver.py")

    if not source_path.exists():
        raise FileNotFoundError(
            f"Could not find {source_path}"
        )

    source_code = source_path.read_text(
        encoding="utf-8"
    )

    print()
    print("SolverForge")
    print("=" * 60)
    print(f"Analyzing: {source_path}")
    print()

    client = NebiusClient()

    analysis = client.analyze_code(
        source_code=source_code,
        filename=str(source_path),
    )

    print("Code analysis")
    print("-" * 60)
    print(analysis.summary)
    print()

    print("Suspected bottleneck")
    print("-" * 60)
    print(analysis.suspected_bottleneck)
    print()

    print("Optimization hypotheses")
    print("=" * 60)

    for index, hypothesis in enumerate(
        analysis.hypotheses,
        start=1,
    ):
        print()
        print(f"{index}. {hypothesis.title}")
        print("-" * 60)

        print("Hypothesis:")
        print(hypothesis.hypothesis)
        print()

        print("Proposed change:")
        print(hypothesis.proposed_change)
        print()

        print("Expected effect:")
        print(hypothesis.expected_effect)
        print()

        print("Risk:")
        print(hypothesis.risk)
        print()

        print(
            "Confidence:",
            hypothesis.confidence,
        )

        print()
        print("Validation:")

        for step in hypothesis.validation_steps:
            print(f"  - {step}")

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()