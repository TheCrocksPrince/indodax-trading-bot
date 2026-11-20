
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class DuplicateWithdrawalError(RuntimeError):
    pass


class WithdrawalJournal:
    """
    Persistent journal for withdrawal requests.

    A reserved request ID must never be reused automatically,
    including after timeouts or process crashes.
    """

    STATUSES = (
        "RESERVED",
        "SUBMITTING",
        "SUCCESS",
        "FAILED",
        "UNKNOWN",
    )

    def __init__(self, db_path="data/withdrawal_journal.db"):
        self.db_path = str(db_path)

        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        self._initialize()

    def _connect(self):
        return sqlite3.connect(
            self.db_path,
            timeout=10.0,
        )

    def _initialize(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS withdrawal_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    withdrawal_type TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    response_json TEXT,
                    UNIQUE(withdrawal_type, request_id)
                )
                """
            )

    @staticmethod
    def _hash_payload(payload):
        serialized = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )

        return hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()

    def reserve(self, withdrawal_type, request_id, payload):
        if withdrawal_type not in ("CRYPTO", "IDR"):
            raise ValueError("Invalid withdrawal type")

        if not isinstance(request_id, str) or not request_id:
            raise ValueError("Invalid request ID")

        if not isinstance(payload, dict):
            raise ValueError("Payload must be a dictionary")

        now = utc_now()
        payload_hash = self._hash_payload(payload)

        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO withdrawal_requests (
                        request_id,
                        withdrawal_type,
                        payload_hash,
                        status,
                        created_at,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        request_id,
                        withdrawal_type,
                        payload_hash,
                        "RESERVED",
                        now,
                        now,
                    ),
                )
        except sqlite3.IntegrityError:
            raise DuplicateWithdrawalError(
                "Withdrawal request ID already exists: "
                "{}".format(request_id)
            )

        return self.get(withdrawal_type, request_id)

    def get(self, withdrawal_type, request_id):
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row

            row = connection.execute(
                """
                SELECT
                    id,
                    request_id,
                    withdrawal_type,
                    payload_hash,
                    status,
                    created_at,
                    updated_at,
                    response_json
                FROM withdrawal_requests
                WHERE withdrawal_type = ?
                  AND request_id = ?
                """,
                (withdrawal_type, request_id),
            ).fetchone()

        if row is None:
            return None

        result = dict(row)

        if result["response_json"] is not None:
            result["response"] = json.loads(
                result.pop("response_json")
            )
        else:
            result.pop("response_json")
            result["response"] = None

        return result

    def mark_submitting(self, withdrawal_type, request_id):
        """
        Persist SUBMITTING before any network call.

        Only RESERVED requests may transition to SUBMITTING.
        """
        now = utc_now()

        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE withdrawal_requests
                SET status = 'SUBMITTING',
                    updated_at = ?
                WHERE withdrawal_type = ?
                  AND request_id = ?
                  AND status = 'RESERVED'
                """,
                (now, withdrawal_type, request_id),
            )

            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Withdrawal cannot enter SUBMITTING"
                )

        return self.get(withdrawal_type, request_id)

    def mark_result(
        self,
        withdrawal_type,
        request_id,
        status,
        response=None,
    ):
        if status not in ("SUCCESS", "FAILED", "UNKNOWN"):
            raise ValueError("Invalid result status")

        response_json = (
            json.dumps(response, default=str)
            if response is not None
            else None
        )

        now = utc_now()

        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE withdrawal_requests
                SET status = ?,
                    response_json = ?,
                    updated_at = ?
                WHERE withdrawal_type = ?
                  AND request_id = ?
                  AND status = 'SUBMITTING'
                """,
                (
                    status,
                    response_json,
                    now,
                    withdrawal_type,
                    request_id,
                ),
            )

            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Withdrawal result transition rejected"
                )

        return self.get(withdrawal_type, request_id)

    def list_requests(self, limit=100):
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be positive")

        with self._connect() as connection:
            connection.row_factory = sqlite3.Row

            rows = connection.execute(
                """
                SELECT
                    request_id,
                    withdrawal_type,
                    status,
                    created_at,
                    updated_at
                FROM withdrawal_requests
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]
