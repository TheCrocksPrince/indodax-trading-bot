from datetime import datetime, timedelta, timezone

import pytest

from app.services.telegram_order_journal import (
    TelegramOrderJournal,
)


def test_confirm_intent_only_once(tmp_path):
    journal = TelegramOrderJournal(
        str(tmp_path / "telegram_orders.db")
    )

    intent_id = journal.create_intent(
        user_id=12345,
        exchange="binance",
        symbol="BTCUSDT",
        side="BUY",
        quantity="0.0001",
        price="70000",
    )

    result = journal.confirm_intent(intent_id, 12345)

    assert result["status"] == "CONFIRMED_PREVIEW"

    with pytest.raises(ValueError):
        journal.confirm_intent(intent_id, 12345)


def test_expired_intent_cannot_be_confirmed(tmp_path):
    journal = TelegramOrderJournal(
        str(tmp_path / "telegram_orders.db")
    )

    intent_id = journal.create_intent(
        user_id=12345,
        exchange="binance",
        symbol="BTCUSDT",
        side="BUY",
        quantity="0.0001",
        price="70000",
    )

    expired_at = (
        datetime.now(timezone.utc)
        - timedelta(minutes=5)
    ).isoformat()

    with journal._connect() as conn:
        conn.execute(
            """
            UPDATE telegram_order_intents
            SET expires_at = ?
            WHERE intent_id = ?
            """,
            (expired_at, intent_id),
        )

    with pytest.raises(ValueError):
        journal.confirm_intent(intent_id, 12345)


def test_other_user_cannot_confirm_intent(tmp_path):
    journal = TelegramOrderJournal(
        str(tmp_path / "telegram_orders.db")
    )

    intent_id = journal.create_intent(
        user_id=12345,
        exchange="binance",
        symbol="BTCUSDT",
        side="BUY",
        quantity="0.0001",
        price="70000",
    )

    with pytest.raises(ValueError):
        journal.confirm_intent(intent_id, 99999)