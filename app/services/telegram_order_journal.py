import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


class TelegramOrderJournal:
    def __init__(self, db_path="data/telegram_orders.db"):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(
            parents=True, exist_ok=True
        )

        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS telegram_order_intents (
                    intent_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    exchange TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity TEXT NOT NULL,
                    price TEXT NOT NULL,
                    status TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

    def _connect(self):
        return sqlite3.connect(
            self.db_path,
            timeout=10
        )

    def create_intent(
        self, user_id, exchange, symbol,
        side, quantity, price
    ):
        intent_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=2)

        with self._connect() as conn:
            conn.execute("""
                INSERT INTO telegram_order_intents
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                intent_id,
                user_id,
                exchange,
                symbol,
                side,
                str(quantity),
                str(price),
                "PENDING_CONFIRMATION",
                expires.isoformat(),
                now.isoformat(),
            ))

        return intent_id

    def confirm_intent(self, intent_id, user_id):
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            cursor = conn.execute("""
                UPDATE telegram_order_intents
                SET status = 'CONFIRMED_PREVIEW'
                WHERE intent_id = ?
                  AND user_id = ?
                  AND status = 'PENDING_CONFIRMATION'
                  AND expires_at > ?
            """, (intent_id, user_id, now))

            if cursor.rowcount != 1:
                raise ValueError(
                    "Intent invalid, expired, or already confirmed"
                )

            record = conn.execute("""
                SELECT exchange, symbol, side,
                       quantity, price, status
                FROM telegram_order_intents
                WHERE intent_id = ?
            """, (intent_id,)).fetchone()

        return {
            "exchange": record[0],
            "symbol": record[1],
            "side": record[2],
            "quantity": record[3],
            "price": record[4],
            "status": record[5],
        }