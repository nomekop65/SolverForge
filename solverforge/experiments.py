from datetime import datetime
from pathlib import Path


def create_experiment_directory(
    root: Path = Path("experiments"),
) -> Path:
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    experiment_dir = (
        root / f"experiment_{timestamp}"
    )

    experiment_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    return experiment_dir