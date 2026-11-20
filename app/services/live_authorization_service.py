import hmac
import sqlite3
from datetime import datetime, timezone

from app.services.bound_live_authorization_journal import (
    BoundLiveAuthorizationJournal,
)
from app.services.telegram_order_journal import (
    TelegramOrderJournal,
)


class LiveAuthorizationService:
    def __init__(
        self,
        telegram_journal=None,
        authorization_journal=None,
    ):
        self.telegram_journal = (
            telegram_journal
            if telegram_journal is not None
            else TelegramOrderJournal()
        )
        self.authorization_journal = (
            authorization_journal
            if authorization_journal is not None
            else BoundLiveAuthorizationJournal()
        )

    def request_authorization(
        self,
        intent_id,
        user_id,
        confirmation,
    ):
        if not hmac.compare_digest(
            str(confirmation),
            "AUTHORIZE LIVE ORDER",
        ):
            raise PermissionError(
                "Explicit live authorization required"
            )

        with self.telegram_journal._connect() as conn:
            conn.row_factory = sqlite3.Row

            row = conn.execute(
                """
                SELECT *
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

        intent = dict(row)

        if intent["status"] != "CONFIRMED_PREVIEW":
            raise PermissionError(
                "Preview confirmation required"
            )

        if intent["exchange"] not in ("binance", "indodax"):
            raise ValueError("Unsupported exchange")

        # This conservative check uses the original
        # preview expiration. A dedicated live approval
        # window will be designed separately.
        expires_at = datetime.fromisoformat(
            intent["expires_at"]
        )

        if expires_at.tzinfo is None:
            raise ValueError("Timezone-aware expiry required")

        if expires_at <= datetime.now(timezone.utc):
            raise PermissionError("Order intent expired")

        order = {
            "intent_id": intent["intent_id"],
            "user_id": intent["user_id"],
            "exchange": intent["exchange"],
            "symbol": intent["symbol"],
            "side": intent["side"],
            "quantity": intent["quantity"],
            "price": intent["price"],
        }

        return self.authorization_journal.authorize(order)