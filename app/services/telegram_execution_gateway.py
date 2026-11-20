from app.clients.binance_execution_client import (
    BinanceExecutionClient,
)
from app.services.telegram_order_journal import (
    TelegramOrderJournal,
)


class TelegramExecutionGateway:
    def __init__(
        self,
        telegram_journal=None,
        binance_execution=None,
    ):
        self.telegram_journal = (
            telegram_journal or TelegramOrderJournal()
        )
        self.binance_execution = (
            binance_execution or BinanceExecutionClient()
        )

    def prepare_binance(self, intent_id, user_id):
        # Read the confirmed Telegram intent.
        with self.telegram_journal._connect() as conn:
            row = conn.execute(
                """
                SELECT exchange, symbol, side,
                       quantity, price, status
                FROM telegram_order_intents
                WHERE intent_id = ?
                  AND user_id = ?
                """,
                (intent_id, user_id),
            ).fetchone()

        if row is None:
            raise PermissionError(
                "Order intent not found or unauthorized"
            )

        exchange, symbol, side, quantity, price, status = row

        if status != "CONFIRMED_PREVIEW":
            raise PermissionError(
                "Order preview has not been confirmed"
            )

        if exchange != "binance":
            raise ValueError(
                "Only Binance preparation is supported"
            )

        # Check whether a Binance journal record
        # already exists for this intent.
        existing = self.binance_execution.journal.get_intent(
            intent_id
        )

        if existing is not None:
            return {
                "status": "ALREADY_PREPARED",
                "intent_id": intent_id,
                "journal_status": existing["status"],
                "submitted": False,
            }

        # Validate and persist. Does not send an order.
        result = self.binance_execution.prepare_order_intent(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            intent_id=intent_id,
        )

        return {
            "status": "PREPARED_NOT_SUBMITTED",
            "intent_id": intent_id,
            "client_order_id": result["client_order_id"],
            "submitted": False,
        }