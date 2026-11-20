import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class ExecutionClaimJournal:
    def __init__(self, db_path="data/execution_claims.db"):
        self.db_path = str(db_path)

        Path(self.db_path).parent.mkdir(
            parents=True, exist_ok=True
        )

        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(
            self.db_path,
            timeout=10,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def _initialize(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_claims (
                    intent_id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

    def claim(self, intent_id, fingerprint):
        if not intent_id or not fingerprint:
            raise ValueError("Invalid execution claim")

        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO execution_claims (
                        intent_id,
                        fingerprint,
                        status,
                        created_at
                    )
                    VALUES (?, ?, 'CLAIMED', ?)
                    """,
                    (
                        intent_id,
                        fingerprint,
                        self._now(),
                    ),
                )

        except sqlite3.IntegrityError as exc:
            raise PermissionError(
                "Execution intent already claimed"
            ) from exc

        return {
            "intent_id": intent_id,
            "fingerprint": fingerprint,
            "status": "CLAIMED",
        }