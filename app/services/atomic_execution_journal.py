import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class AtomicExecutionJournal:
    def __init__(self, db_path="data/atomic_execution.db"):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(
            parents=True, exist_ok=True
        )
        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def _initialize(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS authorizations (
                    intent_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    exchange TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_claims (
                    intent_id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

    def register_authorization(
        self,
        intent_id,
        user_id,
        exchange,
        fingerprint,
        expires_at,
    ):
        if not intent_id or not fingerprint:
            raise ValueError("Invalid authorization")

        if exchange not in ("binance", "indodax"):
            raise ValueError("Unsupported exchange")

        expiry = datetime.fromisoformat(expires_at)

        if expiry.tzinfo is None:
            raise ValueError("Timezone-aware expiry required")

        if expiry <= datetime.now(timezone.utc):
            raise PermissionError("Authorization already expired")

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO authorizations
                (intent_id, user_id, exchange, fingerprint,
                 status, expires_at)
                VALUES (?, ?, ?, ?, 'AUTHORIZED', ?)
                """,
                (
                    intent_id,
                    user_id,
                    exchange,
                    fingerprint,
                    expires_at,
                ),
            )

    def claim_authorized(
        self,
        intent_id,
        user_id,
        exchange,
        fingerprint,
    ):
        conn = self._connect()

        try:
            conn.execute("BEGIN IMMEDIATE")

            cursor = conn.execute(
                """
                UPDATE authorizations
                SET status = 'CONSUMED'
                WHERE intent_id = ?
                  AND user_id = ?
                  AND exchange = ?
                  AND fingerprint = ?
                  AND status = 'AUTHORIZED'
                  AND expires_at > ?
                """,
                (
                    intent_id,
                    user_id,
                    exchange,
                    fingerprint,
                    self._now(),
                ),
            )

            if cursor.rowcount != 1:
                raise PermissionError(
                    "Authorization invalid, expired, or consumed"
                )

            conn.execute(
                """
                INSERT INTO execution_claims
                (intent_id, fingerprint, status, created_at)
                VALUES (?, ?, 'CLAIMED', ?)
                """,
                (
                    intent_id,
                    fingerprint,
                    self._now(),
                ),
            )

            conn.commit()

            return {
                "intent_id": intent_id,
                "fingerprint": fingerprint,
                "status": "CLAIMED",
            }

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()