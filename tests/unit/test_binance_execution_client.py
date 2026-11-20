from unittest.mock import Mock

import pytest

from app.clients.binance_execution_client import (
    BinanceExecutionClient,
)
from app.services.binance_execution_guard import (
    BinanceExecutionGuard,
)


@pytest.fixture
def execution_client(monkeypatch):
    monkeypatch.setenv(
        "BINANCE_ENABLE_LIVE_TRADING", "true"
    )
    monkeypatch.setenv(
        "BINANCE_MAX_ORDER_NOTIONAL_USDT", "10"
    )

    client = Mock()
    transport = Mock()

    client._request.return_value = {
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "status": "TRADING",
                "filters": [
                    {
                        "filterType": "PRICE_FILTER",
                        "minPrice": "0.01",
                        "maxPrice": "1000000",
                        "tickSize": "0.01",
                    },
                    {
                        "filterType": "LOT_SIZE",
                        "minQty": "0.00001",
                        "maxQty": "9000",
                        "stepSize": "0.00001",
                    },
                    {
                        "filterType": "NOTIONAL",
                        "minNotional": "5",
                        "maxNotional": "9000000",
                    },
                ],
            }
        ]
    }

    return BinanceExecutionClient(
        client=client,
        guard=BinanceExecutionGuard(),
        transport=transport,
    )


def test_create_order_requires_confirmation(execution_client):
    with pytest.raises(PermissionError):
        execution_client.create_limit_order(
            "BTCUSDT",
            "BUY",
            "0.00012",
            "50000",
        )

    execution_client.transport.request.assert_not_called()


# def test_create_limit_order_mocked(execution_client):
#     execution_client.transport.request.return_value = {
#         "symbol": "BTCUSDT",
#         "orderId": 12345,
#         "status": "NEW",
#     }

#     result = execution_client.create_limit_order(
#         "BTCUSDT",
#         "BUY",
#         "0.00012",
#         "50000",
#         confirmation="CONFIRM LIVE ORDER",
#     )

#     assert result["orderId"] == 12345

#     args, _ = execution_client.transport.request.call_args

#     assert args[0] == "POST"
#     assert args[1] == "/api/v3/order"
#     assert args[2]["newClientOrderId"].startswith("bot_")

def test_legacy_create_order_blocked(execution_client):
    with pytest.raises(PermissionError):
        execution_client.create_limit_order(
            "BTCUSDT",
            "BUY",
            "0.00012",
            "50000",
            confirmation="CONFIRM LIVE ORDER",
        )

    execution_client.transport.request.assert_not_called()

def test_cancel_order_requires_confirmation(execution_client):
    with pytest.raises(PermissionError):
        execution_client.cancel_order(
            "BTCUSDT",
            12345,
        )

    execution_client.transport.request.assert_not_called()


def test_cancel_order_mocked(execution_client):
    execution_client.transport.request.return_value = {
        "symbol": "BTCUSDT",
        "orderId": 12345,
        "status": "CANCELED",
    }

    result = execution_client.cancel_order(
        "BTCUSDT",
        12345,
        confirmation="CONFIRM CANCEL ORDER",
    )

    assert result["status"] == "CANCELED"

    args, _ = execution_client.transport.request.call_args

    assert args[0] == "DELETE"
    assert args[1] == "/api/v3/order"


def test_live_trading_disabled(monkeypatch):
    monkeypatch.setenv(
        "BINANCE_ENABLE_LIVE_TRADING", "false"
    )

    transport = Mock()

    execution = BinanceExecutionClient(
        client=Mock(),
        guard=BinanceExecutionGuard(),
        transport=transport,
    )

    with pytest.raises(PermissionError):
        execution.create_limit_order(
            "BTCUSDT",
            "BUY",
            "0.00012",
            "50000",
            confirmation="CONFIRM LIVE ORDER",
        )

    transport.request.assert_not_called()