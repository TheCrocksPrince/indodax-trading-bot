import hashlib
import hmac
from unittest.mock import Mock

import httpx

from app.clients.binance_client import BinanceClient


def test_signed_get_signature(monkeypatch):
    monkeypatch.setattr(
        "app.clients.binance_client.time.time",
        lambda: 1700000000.0,
    )

    captured = {}

    def handler(request):
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["headers"] = request.headers

        return httpx.Response(
            200,
            json={"balances": []},
        )

    transport = httpx.MockTransport(handler)

    original_client = httpx.Client

    def mock_client(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(
        "app.clients.binance_client.httpx.Client",
        mock_client,
    )

    client = BinanceClient(
        api_key="test-api-key",
        secret_key="test-secret",
    )

    client.get_account()

    payload = (
        "timestamp=1700000000000"
        "&recvWindow=5000"
    )

    expected_signature = hmac.new(
        b"test-secret",
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    assert captured["method"] == "GET"
    assert (
        f"signature={expected_signature}"
        in captured["url"]
    )
    assert (
        captured["headers"]["X-MBX-APIKEY"]
        == "test-api-key"
    )