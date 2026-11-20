
import json
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List


def _json_default(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    raise TypeError("Unsupported type: {}".format(type(value).__name__))


class PaperTradeStore:
    """Penyimpanan lokal untuk transaksi simulasi, bukan order live."""

    def __init__(self, db_path="data/paper_trading.db"):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _initialize(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS paper_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity TEXT NOT NULL,
                    notional TEXT NOT NULL,
                    fee TEXT NOT NULL,
                    average_price TEXT NOT NULL,
                    details_json TEXT NOT NULL
                )
                """
            )

    def save_trade(self, trade: Dict[str, Any]) -> int:
        """Simpan satu hasil transaksi paper trading."""
        created_at = datetime.now(timezone.utc).isoformat()
        symbol = "{}{}".format(
            trade["base_asset"].upper(),
            trade["quote_asset"].upper(),
        )

        details_json = json.dumps(
            trade,
            default=_json_default,
            ensure_ascii=False,
        )

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO paper_trades (
                    created_at, symbol, side, quantity,
                    notional, fee, average_price, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    symbol,
                    trade["side"].upper(),
                    str(trade["quantity"]),
                    str(trade["notional"]),
                    str(trade["fee"]),
                    str(trade["average_price"]),
                    details_json,
                ),
            )
            return int(cursor.lastrowid)

    def list_trades(self, limit=100) -> List[Dict[str, Any]]:
        if limit <= 0:
            raise ValueError("limit must be positive")

        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT id, created_at, symbol, side, quantity,
                       notional, fee, average_price, details_json
                FROM paper_trades
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        results = []
        for row in rows:
            item = dict(row)
            item["details"] = json.loads(item.pop("details_json"))
            results.append(item)

        return results
