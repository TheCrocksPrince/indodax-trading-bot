from unittest.mock import Mock

import pytest

from app.clients.binance_execution_transport import (
    BinanceExecutionTransport,
)


@pytest.mark.parametrize(
    "method",
    ["POST", "DELETE"],
)
def test_production_execution_is_locked(
    monkeypatch,
    method,
):
    # Even an accidental live flag cannot unlock transport.
    monkeypatch.setenv(
        "BINANCE_ENABLE_LIVE_TRADING",
        "true",
    )

    client = Mock()
    http_client = Mock()

    transport = BinanceExecutionTransport(
        client=client,
        http_client=http_client,
    )

    with pytest.raises(PermissionError):
        transport.request(
            method,
            "/api/v3/order",
            {"symbol": "BTCUSDT"},
        )

    http_client.request.assert_not_called()


def test_production_transport_rejects_test_order(
    monkeypatch,
):
    monkeypatch.setenv(
        "BINANCE_ENABLE_LIVE_TRADING",
        "true",
    )

    http_client = Mock()

    transport = BinanceExecutionTransport(
        client=Mock(),
        http_client=http_client,
    )

    with pytest.raises(PermissionError):
        transport.request(
            "POST",
            "/api/v3/order/test",
            {"symbol": "BTCUSDT"},
        )

    http_client.request.assert_not_called()