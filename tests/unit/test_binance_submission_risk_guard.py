from unittest.mock import Mock

import pytest

from app.services.binance_order_submission import (
    BinanceOrderSubmission,
)


def test_submission_rejects_order_exceeding_risk_limit():
    journal = Mock()
    transport = Mock()
    guard = Mock()

    journal.get_intent.return_value = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": "1",
        "price": "100000",
        "client_order_id": "bot_test",
    }

    guard.validate.side_effect = PermissionError(
        "Order exceeds configured notional limit"
    )

    submission = BinanceOrderSubmission(
        journal=journal,
        transport=transport,
        guard=guard,
    )

    with pytest.raises(PermissionError):
        submission.submit_prepared_intent("intent_1")

    journal.claim_for_submission.assert_not_called()
    transport.request.assert_not_called()


def test_submission_validates_before_claim():
    journal = Mock()
    transport = Mock()
    guard = Mock()

    journal.transition.return_value = {
        "status": "ACKNOWLEDGED"
    }

    journal.get_intent.return_value = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": "0.0001",
        "price": "70000",
        "client_order_id": "bot_test",
    }

    transport.request.return_value = {
        "symbol": "BTCUSDT",
        "clientOrderId": "bot_test",
        "orderId": 123,
        "status": "NEW",
    }

    submission = BinanceOrderSubmission(
        journal=journal,
        transport=transport,
        guard=guard,
    )

    submission.submit_prepared_intent("intent_1")

    guard.validate.assert_called_once()

    assert (
        guard.validate.call_args.kwargs["symbol"]
        == "BTCUSDT"
    )

    journal.claim_for_submission.assert_called_once_with(
        "intent_1"
    )

    transport.request.assert_called_once()