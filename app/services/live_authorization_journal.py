import sqlite3
from datetime import datetime, timedelta, timezone


class LiveAuthorizationJournal:
    def __init__(self, db_path="data/live_authorizations.db"):
        self.db_path = str(db_path)
        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _now():
        return datetime.now(timezone.utc)

    def _initialize(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS live_authorizations (
                    intent_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    exchange TEXT NOT NULL,
                    status TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

    def authorize(self, intent_id, user_id, exchange):
        now = self._now()
        expires_at = now + timedelta(seconds=60)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO live_authorizations (
                    intent_id, user_id, exchange,
                    status, expires_at, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    intent_id,
                    user_id,
                    exchange,
                    "AUTHORIZED",
                    expires_at.isoformat(),
                    now.isoformat(),
                ),
            )

        return {
            "intent_id": intent_id,
            "exchange": exchange,
            "status": "AUTHORIZED",
            "expires_at": expires_at.isoformat(),
        }

    def consume(self, intent_id, user_id):
        now = self._now().isoformat()

        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE live_authorizations
                SET status = 'CONSUMED'
                WHERE intent_id = ?
                  AND user_id = ?
                  AND status = 'AUTHORIZED'
                  AND expires_at > ?
                """,
                (intent_id, user_id, now),
            )

            if cursor.rowcount != 1:
                raise PermissionError(
                    "Authorization missing, expired, or consumed"
                )

        return True