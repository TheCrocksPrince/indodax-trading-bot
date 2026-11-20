from unittest.mock import Mock

import pytest

from scripts.binance_order_journal import (
    BinanceOrderJournal,
)
from app.services.binance_order_reconciliation import (
    BinanceOrderReconciliation,
)


@pytest.fixture
def setup(tmp_path):
    journal = BinanceOrderJournal(
        tmp_path / "reconciliation.db"
    )

    journal.create_intent(
        intent_id="intent-001",
        client_order_id="bot_001",
        symbol="BTCUSDT",
        side="BUY",
        quantity="0.00012",
        price="50000",
    )

    journal.claim_for_submission("intent-001")

    journal.transition(
        "intent-001",
        "SUBMITTING",
        "UNKNOWN",
    )

    lookup = Mock()

    lookup.get_order_by_client_id.return_value = {
        "symbol": "BTCUSDT",
        "clientOrderId": "bot_001",
        "orderId": 12345,
        "status": "NEW",
    }

    service = BinanceOrderReconciliation(
        journal=journal,
        lookup_client=lookup,
    )

    return journal, lookup, service


def test_unknown_order_found(setup):
    journal, lookup, service = setup

    result = service.reconcile("intent-001")

    assert result["status"] == "ACKNOWLEDGED"
    assert result["exchange_status"] == "NEW"

    assert (
        journal.get_intent("intent-001")["status"]
        == "ACKNOWLEDGED"
    )

    lookup.get_order_by_client_id.assert_called_once_with(
        symbol="BTCUSDT",
        client_order_id="bot_001",
    )


def test_lookup_timeout_preserves_unknown(setup):
    journal, lookup, service = setup

    lookup.get_order_by_client_id.side_effect = (
        TimeoutError("Lookup timed out")
    )

    result = service.reconcile("intent-001")

    assert result["status"] == "UNKNOWN"
    assert result["action"] == "RETRY_LOOKUP_LATER"

    assert (
        journal.get_intent("intent-001")["status"]
        == "UNKNOWN"
    )


def test_order_not_found_preserves_unknown(setup):
    journal, lookup, service = setup

    lookup.get_order_by_client_id.side_effect = (
        RuntimeError("Order does not exist")
    )

    result = service.reconcile("intent-001")

    assert result["status"] == "UNKNOWN"


def test_mismatched_client_order_id(setup):
    journal, lookup, service = setup

    lookup.get_order_by_client_id.return_value = {
        "symbol": "BTCUSDT",
        "clientOrderId": "different_order",
        "orderId": 12345,
        "status": "NEW",
    }

    result = service.reconcile("intent-001")

    assert result["status"] == "UNKNOWN"
    assert result["action"] == "UNVERIFIED_RESPONSE"


def test_missing_intent(setup):
    journal, lookup, service = setup

    with pytest.raises(ValueError):
        service.reconcile("missing-intent")

    lookup.get_order_by_client_id.assert_not_called()


def test_already_acknowledged(setup):
    journal, lookup, service = setup

    service.reconcile("intent-001")
    lookup.reset_mock()

    result = service.reconcile("intent-001")

    assert result["action"] == "ALREADY_RECONCILED"
    lookup.get_order_by_client_id.assert_not_called()


def test_submitting_requires_explicit_recovery(setup):
    journal, lookup, service = setup

    journal.create_intent(
        intent_id="intent-002",
        client_order_id="bot_002",
        symbol="BTCUSDT",
        side="BUY",
        quantity="0.00012",
        price="50000",
    )

    journal.claim_for_submission("intent-002")

    with pytest.raises(RuntimeError):
        service.reconcile("intent-002")

    assert (
        journal.get_intent("intent-002")["status"]
        == "SUBMITTING"
    )


def test_explicit_stale_recovery(setup):
    journal, lookup, service = setup

    journal.create_intent(
        intent_id="intent-002",
        client_order_id="bot_002",
        symbol="BTCUSDT",
        side="BUY",
        quantity="0.00012",
        price="50000",
    )

    journal.claim_for_submission("intent-002")

    lookup.get_order_by_client_id.return_value = {
        "symbol": "BTCUSDT",
        "clientOrderId": "bot_002",
        "orderId": 67890,
        "status": "NEW",
    }

    result = service.reconcile(
        "intent-002",
        recover_stale=True,
    )

    assert result["status"] == "ACKNOWLEDGED"

    assert (
        journal.get_intent("intent-002")["status"]
        == "ACKNOWLEDGED"
    )