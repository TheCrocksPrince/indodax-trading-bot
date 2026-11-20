from unittest.mock import Mock

import pytest

from app.clients.binance_execution_client import (
    BinanceExecutionClient,
)
from scripts.binance_order_journal import (
    BinanceOrderJournal,
    DuplicateOrderIntentError,
)


@pytest.fixture
def execution(tmp_path):
    journal = BinanceOrderJournal(
        tmp_path / "orders.db"
    )

    client = BinanceExecutionClient(
        client=Mock(),
        transport=Mock(),
        journal=journal,
    )

    # Mock only the already-tested validation layer.
    client.prepare_limit_order = Mock(
        return_value={
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": "0.00012",
            "price": "50000",
            "notional_usdt": "6.00000",
            "status": "VALIDATED_NOT_SUBMITTED",
        }
    )

    return client


def prepare(execution, intent_id):
    return execution.prepare_order_intent(
        symbol="BTCUSDT",
        side="BUY",
        quantity="0.00012",
        price="50000",
        intent_id=intent_id,
    )


def test_prepare_persists_intent(execution):
    result = prepare(execution, "intent-001")

    assert result["status"] == "PENDING"
    assert result["submission_status"] == "NOT_SUBMITTED"

    saved = execution.journal.get_intent("intent-001")

    assert saved is not None
    assert saved["client_order_id"] == result["client_order_id"]


def test_duplicate_intent_cannot_be_prepared_twice(execution):
    prepare(execution, "intent-001")

    with pytest.raises(DuplicateOrderIntentError):
        prepare(execution, "intent-001")


def test_preparation_never_submits_order(execution):
    prepare(execution, "intent-001")

    execution.transport.request.assert_not_called()


def test_different_intents_get_different_client_ids(execution):
    first = prepare(execution, "intent-001")
    second = prepare(execution, "intent-002")

    assert first["client_order_id"] != second["client_order_id"]


def test_missing_intent_id_rejected(execution):
    with pytest.raises(ValueError):
        prepare(execution, "")