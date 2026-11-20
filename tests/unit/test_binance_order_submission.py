from unittest.mock import Mock

import httpx
import pytest

from scripts.binance_order_journal import (
    BinanceOrderJournal,
    InvalidOrderTransitionError,
)
from app.services.binance_order_submission import (
    BinanceOrderSubmission,
)


@pytest.fixture
def setup(tmp_path):
    journal = BinanceOrderJournal(
        tmp_path / "orders.db"
    )

    journal.create_intent(
        intent_id="intent-001",
        client_order_id="bot_001",
        symbol="BTCUSDT",
        side="BUY",
        quantity="0.00012",
        price="50000",
    )

    transport = Mock()

    transport.request.return_value = {
        "symbol": "BTCUSDT",
        "orderId": 12345,
        "clientOrderId": "bot_001",
        "status": "NEW",
    }

    submission = BinanceOrderSubmission(
        journal=journal,
        transport=transport,
    )

    return journal, transport, submission


def test_submission_acknowledged(setup):
    journal, transport, submission = setup

    result = submission.submit_prepared_intent(
        "intent-001"
    )

    assert result["journal_status"] == "ACKNOWLEDGED"
    assert result["exchange_status"] == "NEW"
    assert result["exchange_order_id"] == 12345

    transport.request.assert_called_once()


def test_duplicate_submission_blocked(setup):
    journal, transport, submission = setup

    submission.submit_prepared_intent("intent-001")

    with pytest.raises(InvalidOrderTransitionError):
        submission.submit_prepared_intent("intent-001")

    transport.request.assert_called_once()


def test_timeout_marks_unknown(setup):
    journal, transport, submission = setup

    transport.request.side_effect = httpx.TimeoutException(
        "Request timed out"
    )

    with pytest.raises(httpx.TimeoutException):
        submission.submit_prepared_intent("intent-001")

    record = journal.get_intent("intent-001")

    assert record["status"] == "UNKNOWN"


def test_timeout_cannot_be_resubmitted(setup):
    journal, transport, submission = setup

    transport.request.side_effect = httpx.TimeoutException(
        "Request timed out"
    )

    with pytest.raises(httpx.TimeoutException):
        submission.submit_prepared_intent("intent-001")

    with pytest.raises(InvalidOrderTransitionError):
        submission.submit_prepared_intent("intent-001")

    transport.request.assert_called_once()


def test_unknown_exchange_response(setup):
    journal, transport, submission = setup

    transport.request.return_value = {
        "symbol": "BTCUSDT",
        "status": "NEW",
    }

    with pytest.raises(RuntimeError):
        submission.submit_prepared_intent("intent-001")

    assert (
        journal.get_intent("intent-001")["status"]
        == "UNKNOWN"
    )


def test_missing_intent_never_submits(setup):
    journal, transport, submission = setup

    with pytest.raises(ValueError):
        submission.submit_prepared_intent(
            "nonexistent-intent"
        )

    transport.request.assert_not_called()