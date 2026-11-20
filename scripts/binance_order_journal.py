import sqlite3
from datetime import datetime, timezone


class DuplicateOrderIntentError(Exception):
    pass


class InvalidOrderTransitionError(Exception):
    pass


class BinanceOrderJournal:
    STATUSES = {
        "PENDING",
        "SUBMITTING",
        "ACKNOWLEDGED",
        "UNKNOWN",
        "REJECTED",
    }

    def __init__(self, db_path="data/binance_orders.db"):
        self.db_path = str(db_path)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(
            self.db_path,
            timeout=10,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def _initialize(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS binance_order_intents (
                    intent_id TEXT PRIMARY KEY,
                    client_order_id TEXT NOT NULL UNIQUE,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity TEXT NOT NULL,
                    price TEXT NOT NULL,
                    status TEXT NOT NULL,
                    exchange_order_id TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

    def create_intent(
        self,
        intent_id,
        client_order_id,
        symbol,
        side,
        quantity,
        price,
    ):
        if not intent_id or not client_order_id:
            raise ValueError("Order IDs cannot be empty")

        if not all([symbol, side, quantity, price]):
            raise ValueError("Incomplete order intent")

        now = self._now()

        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO binance_order_intents (
                        intent_id,
                        client_order_id,
                        symbol,
                        side,
                        quantity,
                        price,
                        status,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        intent_id,
                        client_order_id,
                        symbol,
                        side,
                        str(quantity),
                        str(price),
                        "PENDING",
                        now,
                        now,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateOrderIntentError(
                "Order intent or client order ID already exists"
            ) from exc

        return self.get_intent(intent_id)

    def get_intent(self, intent_id):
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM binance_order_intents
                WHERE intent_id = ?
                """,
                (intent_id,),
            ).fetchone()

        return dict(row) if row else None

    def get_by_client_order_id(self, client_order_id):
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM binance_order_intents
                WHERE client_order_id = ?
                """,
                (client_order_id,),
            ).fetchone()

        return dict(row) if row else None

    def transition(
        self,
        intent_id,
        expected_status,
        new_status,
        exchange_order_id=None,
        error_message=None,
    ):
        if new_status not in self.STATUSES:
            raise ValueError("Invalid order status")

        allowed = {
            "PENDING": {"SUBMITTING"},
            "SUBMITTING": {
                "ACKNOWLEDGED",
                "UNKNOWN",
                "REJECTED",
            },
            "UNKNOWN": {"ACKNOWLEDGED", "REJECTED"},
            "ACKNOWLEDGED": set(),
            "REJECTED": set(),
        }

        if new_status not in allowed.get(
            expected_status, set()
        ):
            raise InvalidOrderTransitionError(
                "Invalid status transition"
            )

        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE binance_order_intents
                SET status = ?,
                    exchange_order_id = COALESCE(
                        ?, exchange_order_id
                    ),
                    error_message = ?,
                    updated_at = ?
                WHERE intent_id = ?
                  AND status = ?
                """,
                (
                    new_status,
                    (
                        str(exchange_order_id)
                        if exchange_order_id is not None
                        else None
                    ),
                    error_message,
                    self._now(),
                    intent_id,
                    expected_status,
                ),
            )

            if cursor.rowcount != 1:
                raise InvalidOrderTransitionError(
                    "Intent missing or status already changed"
                )

        return self.get_intent(intent_id)

    def claim_for_submission(self, intent_id):
        """
        Atomic transition:
        PENDING -> SUBMITTING

        Only one caller can successfully claim an intent.
        """
        return self.transition(
            intent_id,
            "PENDING",
            "SUBMITTING",
        )