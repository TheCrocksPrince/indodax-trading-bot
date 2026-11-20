from unittest.mock import Mock

import pytest

from app.clients.binance_client import BinanceClient


def test_read_only_default():
    client = BinanceClient(
        api_key="dummy",
        secret_key="dummy",
    )

    assert client.read_only is True


def test_read_only_cannot_be_disabled():
    with pytest.raises(PermissionError):
        BinanceClient(read_only=False)


@pytest.mark.parametrize(
    "method",
    ["POST", "PUT", "PATCH", "DELETE"],
)
def test_production_rejects_write_methods(method):
    client = BinanceClient(
        api_key="dummy",
        secret_key="dummy",
    )

    with pytest.raises(PermissionError):
        client._request(
            method,
            "/api/v3/order",
            {"symbol": "BTCUSDT"},
        )


def test_production_rejects_unknown_endpoint():
    client = BinanceClient(
        api_key="dummy",
        secret_key="dummy",
    )

    with pytest.raises(PermissionError):
        client._request(
            "GET",
            "/api/v3/unknown",
        )


def test_signed_order_lookup_stays_read_only():
    client = BinanceClient(
        api_key="dummy",
        secret_key="dummy",
    )

    client._request = Mock(
        return_value={
            "symbol": "BTCUSDT",
            "clientOrderId": "bot_001",
            "orderId": 12345,
            "status": "NEW",
        }
    )

    client.get_order_by_client_id(
        "BTCUSDT",
        "bot_001",
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