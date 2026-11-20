import os
from datetime import datetime, timezone
from decimal import Decimal

from app.clients.binance_execution_client import BinanceExecutionClient
from app.clients.indodax_client import create_indodax_client
from app.services.binance_execution_guard import BinanceExecutionGuard
from app.services.order_fingerprint import order_fingerprint
from app.services.telegram_order_journal import TelegramOrderJournal


class DualExchangeExecution:
    def __init__(self):
        self.telegram = TelegramOrderJournal()

    def get_confirmed_intent(self, intent_id, user_id):
        with self.telegram._connect() as conn:
            row = conn.execute(
                """
                SELECT exchange, symbol, side, quantity,
                       price, status, expires_at
                FROM telegram_order_intents
                WHERE intent_id = ? AND user_id = ?
                """,
                (intent_id, user_id),
            ).fetchone()

        if row is None:
            raise PermissionError("Intent not found")

        exchange, symbol, side, quantity, price, status, expiry = row

        if status != "CONFIRMED_PREVIEW":
            raise PermissionError("Preview not confirmed")

        expires_at = datetime.fromisoformat(expiry)

        if expires_at.tzinfo is None or expires_at <= datetime.now(timezone.utc):
            raise PermissionError("Intent expired")

        return {
            "intent_id": intent_id,
            "user_id": user_id,
            "exchange": exchange,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
        }

    def prepare(self, intent_id, user_id):
        order = self.get_confirmed_intent(intent_id, user_id)

        fingerprint = order_fingerprint(**order)

        if order["exchange"] == "binance":
            execution = BinanceExecutionClient()
            prepared = execution.prepare_limit_order(
                order["symbol"],
                order["side"],
                order["quantity"],
                order["price"],
            )

            return {
                **order,
                "fingerprint": fingerprint,
                "validation": prepared["status"],
                "submitted": False,
            }

        if order["exchange"] == "indodax":
            if not order["symbol"].endswith("IDR"):
                raise ValueError("Only IDR pairs supported")

            notional = (
                Decimal(order["quantity"]) * Decimal(order["price"])
            )

            max_idr = Decimal(
                os.getenv("INDODAX_MAX_ORDER_NOTIONAL_IDR", "100000")
            )

            if (
                not max_idr.is_finite()
                or max_idr <= 0
                or notional > max_idr
            ):
                raise PermissionError("Indodax notional limit exceeded")

            result = create_indodax_client().create_order(
                symbol=order["symbol"],
                side=order["side"],
                quantity=order["quantity"],
                price=order["price"],
                order_type="LIMIT",
                dry_run=True,
            )

            if result.get("sent") is not False:
                raise RuntimeError("Unexpected dry-run result")

            return {
                **order,
                "fingerprint": fingerprint,
                "validation": "DRY_RUN_VALIDATED",
                "notional_idr": str(notional),
                "submitted": False,
            }

        raise ValueError("Unsupported exchange")