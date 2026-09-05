import sqlite3
from pathlib import Path

from solverforge.history.schemas import ExperimentRecord


DEFAULT_DATABASE_PATH = Path(
    "data/solverforge.db"
)


class ExperimentRepository:
    def __init__(
        self,
        database_path: Path = DEFAULT_DATABASE_PATH,
    ) -> None:
        self.database_path = database_path

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize_database()

    def _connect(
        self,
    ) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path
        )

        connection.row_factory = sqlite3.Row

        return connection

    def _initialize_database(
        self,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,

                    parent_id TEXT,

                    source_file TEXT NOT NULL,
                    candidate_file TEXT NOT NULL,

                    hypothesis_title TEXT NOT NULL,
                    hypothesis TEXT NOT NULL,
                    proposed_change TEXT NOT NULL,
                    confidence TEXT NOT NULL,

                    baseline_median REAL NOT NULL,

                    candidate_median REAL,
                    speedup REAL,
                    runtime_change_percent REAL,

                    verification_passed INTEGER NOT NULL,
                    stdout_match INTEGER NOT NULL,

                    status TEXT NOT NULL
                )
                """
            )

            connection.commit()

    def save(
        self,
        experiment: ExperimentRecord,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO experiments (
                    experiment_id,
                    timestamp,
                    parent_id,
                    source_file,
                    candidate_file,
                    hypothesis_title,
                    hypothesis,
                    proposed_change,
                    confidence,
                    baseline_median,
                    candidate_median,
                    speedup,
                    runtime_change_percent,
                    verification_passed,
                    stdout_match,
                    status
                )
                VALUES (
                    :experiment_id,
                    :timestamp,
                    :parent_id,
                    :source_file,
                    :candidate_file,
                    :hypothesis_title,
                    :hypothesis,
                    :proposed_change,
                    :confidence,
                    :baseline_median,
                    :candidate_median,
                    :speedup,
                    :runtime_change_percent,
                    :verification_passed,
                    :stdout_match,
                    :status
                )
                """,
                {
                    **experiment.model_dump(),
                    "verification_passed": int(
                        experiment.verification_passed
                    ),
                    "stdout_match": int(
                        experiment.stdout_match
                    ),
                },
            )

            connection.commit()

    def get(
        self,
        experiment_id: str,
    ) -> ExperimentRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM experiments
                WHERE experiment_id = ?
                """,
                (experiment_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_record(row)

    def list_recent(
        self,
        limit: int = 10,
    ) -> list[ExperimentRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM experiments
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            self._row_to_record(row)
            for row in rows
        ]

    def _row_to_record(
        self,
        row: sqlite3.Row,
    ) -> ExperimentRecord:
        return ExperimentRecord(
            experiment_id=row["experiment_id"],
            timestamp=row["timestamp"],
            parent_id=row["parent_id"],
            source_file=row["source_file"],
            candidate_file=row["candidate_file"],
            hypothesis_title=row[
                "hypothesis_title"
            ],
            hypothesis=row["hypothesis"],
            proposed_change=row[
                "proposed_change"
            ],
            confidence=row["confidence"],
            baseline_median=row[
                "baseline_median"
            ],
            candidate_median=row[
                "candidate_median"
            ],
            speedup=row["speedup"],
            runtime_change_percent=row[
                "runtime_change_percent"
            ],
            verification_passed=bool(
                row["verification_passed"]
            ),
            stdout_match=bool(
                row["stdout_match"]
            ),
            status=row["status"],
        )