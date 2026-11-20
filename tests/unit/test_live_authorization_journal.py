import pytest

from app.services.live_authorization_journal import (
    LiveAuthorizationJournal,
)


def test_authorization_can_be_consumed_once(tmp_path):
    journal = LiveAuthorizationJournal(
        tmp_path / "auth.db"
    )

    journal.authorize(
        "intent-001",
        12345,
        "binance",
    )

    assert journal.consume("intent-001", 12345) is True

    with pytest.raises(PermissionError):
        journal.consume("intent-001", 12345)


def test_other_user_cannot_consume(tmp_path):
    journal = LiveAuthorizationJournal(
        tmp_path / "auth.db"
    )

    journal.authorize(
        "intent-002",
        12345,
        "binance",
    )

    with pytest.raises(PermissionError):
        journal.consume("intent-002", 99999)


def test_missing_authorization_rejected(tmp_path):
    journal = LiveAuthorizationJournal(
        tmp_path / "auth.db"
    )

    with pytest.raises(PermissionError):
        journal.consume("missing", 12345)