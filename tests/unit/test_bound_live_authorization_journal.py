import sqlite3

import pytest

from app.services.bound_live_authorization_journal import (
    BoundLiveAuthorizationJournal,
)


ORDER = {
    "intent_id": "intent-001",
    "user_id": 12345,
    "exchange": "binance",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "quantity": "0.0001",
    "price": "70000",
}


def test_valid_authorization_consumed_once(tmp_path):
    journal = BoundLiveAuthorizationJournal(tmp_path / "auth.db")

    journal.authorize(ORDER)

    assert journal.consume(ORDER) is True

    with pytest.raises(PermissionError):
        journal.consume(ORDER)


@pytest.mark.parametrize(
    "field,value",
    [
        ("user_id", 99999),
        ("exchange", "indodax"),
        ("symbol", "ETHUSDT"),
        ("side", "SELL"),
        ("quantity", "0.0002"),
        ("price", "71000"),
        ("intent_id", "different-intent"),
    ],
)
def test_modified_order_rejected(tmp_path, field, value):
    journal = BoundLiveAuthorizationJournal(tmp_path / "auth.db")
    journal.authorize(ORDER)

    modified = {**ORDER, field: value}

    with pytest.raises(PermissionError):
        journal.consume(modified)

    # Failed attempt must not consume the original authorization.
    assert journal.consume(ORDER) is True


def test_duplicate_authorization_rejected(tmp_path):
    journal = BoundLiveAuthorizationJournal(tmp_path / "auth.db")

    journal.authorize(ORDER)

    with pytest.raises(PermissionError):
        journal.authorize(ORDER)


def test_expired_authorization_rejected(tmp_path):
    db_path = tmp_path / "auth.db"
    journal = BoundLiveAuthorizationJournal(db_path)
    journal.authorize(ORDER)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            UPDATE bound_live_authorizations
            SET expires_at = '2000-01-01T00:00:00+00:00'
            WHERE intent_id = ?
            """,
            (ORDER["intent_id"],),
        )

    with pytest.raises(PermissionError):
        journal.consume(ORDER)