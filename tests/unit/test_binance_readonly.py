import pytest
import httpx

from app.clients.binance_client import BinanceClient


@pytest.fixture
def client(monkeypatch):
    def block_network(*args, **kwargs):
        pytest.fail("Unexpected network request")

    monkeypatch.setattr(
        httpx.Client,
        "request",
        block_network,
    )

    return BinanceClient(
        base_url="https://api.binance.com",
        api_key="",
        secret_key="",
    )


def test_production_blocks_post(client):
    with pytest.raises(PermissionError, match="READ-ONLY"):
        client._request(
            "POST",
            "/api/v3/order",
            {"symbol": "BTCUSDT"},
        )


def test_production_blocks_test_order(client):
    with pytest.raises(PermissionError, match="READ-ONLY"):
        client.test_order(
            symbol="BTCUSDT",
            side="BUY",
            quantity="0.001",
            price="50000",
        )


def test_production_blocks_unknown_endpoint(client):
    with pytest.raises(PermissionError, match="allowlisted"):
        client._request(
            "GET",
            "/api/v3/unknown",
        )