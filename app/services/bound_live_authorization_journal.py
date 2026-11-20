import sqlite3
from datetime import datetime, timedelta, timezone

from app.services.order_fingerprint import order_fingerprint


class BoundLiveAuthorizationJournal:
    def __init__(self, db_path="data/bound_live_authorizations.db"):
        self.db_path = str(db_path)
        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    @staticmethod
    def _now():
        return datetime.now(timezone.utc)

    def _initialize(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bound_live_authorizations (
                    intent_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    exchange TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

    def authorize(self, order, ttl_seconds=60):
        if not 1 <= ttl_seconds <= 300:
            raise ValueError("Invalid authorization TTL")

        fingerprint = order_fingerprint(**order)
        now = self._now()
        expires_at = now + timedelta(seconds=ttl_seconds)

        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO bound_live_authorizations
                    (intent_id, user_id, exchange, fingerprint,
                     status, expires_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order["intent_id"],
                        order["user_id"],
                        order["exchange"].lower(),
                        fingerprint,
                        "AUTHORIZED",
                        expires_at.isoformat(),
                        now.isoformat(),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise PermissionError(
                "Authorization already exists for this intent"
            ) from exc

        return {
            "intent_id": order["intent_id"],
            "status": "AUTHORIZED",
            "fingerprint": fingerprint,
            "expires_at": expires_at.isoformat(),
        }

    def consume(self, order):
        fingerprint = order_fingerprint(**order)

        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE bound_live_authorizations
                SET status = 'CONSUMED'
                WHERE intent_id = ?
                  AND user_id = ?
                  AND exchange = ?
                  AND fingerprint = ?
                  AND status = 'AUTHORIZED'
                  AND expires_at > ?
                """,
                (
                    order["intent_id"],
                    order["user_id"],
                    order["exchange"].lower(),
                    fingerprint,
                    self._now().isoformat(),
                ),
            )

            if cursor.rowcount != 1:
                raise PermissionError(
                    "Authorization invalid, expired, or consumed"
                )

        return True