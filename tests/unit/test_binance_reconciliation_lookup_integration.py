from unittest.mock import Mock

from app.clients.binance_client import BinanceClient
from scripts.binance_order_journal import (
    BinanceOrderJournal,
)
from app.services.binance_order_reconciliation import (
    BinanceOrderReconciliation,
)


def test_reconciliation_uses_signed_lookup(tmp_path):
    journal = BinanceOrderJournal(
        tmp_path / "orders.db"
    )

    journal.create_intent(
        intent_id="integration-001",
        client_order_id="bot_integration_001",
        symbol="BTCUSDT",
        side="BUY",
        quantity="0.00012",
        price="50000",
    )

    journal.claim_for_submission("integration-001")

    journal.transition(
        "integration-001",
        "SUBMITTING",
        "UNKNOWN",
    )

    client = BinanceClient.__new__(BinanceClient)

    client._request = Mock(
        return_value={
            "symbol": "BTCUSDT",
            "clientOrderId": "bot_integration_001",
            "orderId": 98765,
            "status": "NEW",
        }
    )

    reconciliation = BinanceOrderReconciliation(
        journal=journal,
        lookup_client=client,
    )

    result = reconciliation.reconcile(
        "integration-001"
    )

    assert result["status"] == "ACKNOWLEDGED"

    client._request.assert_called_once_with(
        "GET",
        "/api/v3/order",
        {
            "symbol": "BTCUSDT",
            "origClientOrderId": "bot_integration_001",
        },
        signed=True,
    )

    assert (
        journal.get_intent("integration-001")["status"]
        == "ACKNOWLEDGED"
    )