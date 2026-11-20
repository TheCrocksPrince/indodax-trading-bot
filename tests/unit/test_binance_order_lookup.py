from unittest.mock import Mock

import pytest

from app.clients.binance_client import BinanceClient


@pytest.fixture
def client():
    # Avoid initializing real HTTP connections.
    instance = BinanceClient.__new__(BinanceClient)

    instance._request = Mock(
        return_value={
            "symbol": "BTCUSDT",
            "orderId": 12345,
            "clientOrderId": "bot_001",
            "status": "NEW",
        }
    )

    return instance


def test_lookup_uses_signed_get(client):
    result = client.get_order_by_client_id(
        symbol="BTCUSDT",
        client_order_id="bot_001",
    )

    client._request.assert_called_once_with(
        "GET",
        "/api/v3/order",
        {
            "symbol": "BTCUSDT",
            "origClientOrderId": "bot_001",
        },
        signed=True,
    )

    assert result["orderId"] == 12345


def test_lookup_normalizes_symbol(client):
    client.get_order_by_client_id(
        symbol="btcusdt",
        client_order_id="bot_001",
    )

    assert (
        client._request.call_args.args[2]["symbol"]
        == "BTCUSDT"
    )


def test_missing_client_order_id_rejected(client):
    with pytest.raises(ValueError):
        client.get_order_by_client_id(
            symbol="BTCUSDT",
            client_order_id="",
        )

    client._request.assert_not_called()


def test_invalid_client_order_id_rejected(client):
    with pytest.raises(ValueError):
        client.get_order_by_client_id(
            symbol="BTCUSDT",
            client_order_id="bad id!",
        )

    client._request.assert_not_called()


def test_invalid_symbol_rejected(client):
    with pytest.raises(ValueError):
        client.get_order_by_client_id(
            symbol="BTC/USDT",
            client_order_id="bot_001",
        )

    client._request.assert_not_called()