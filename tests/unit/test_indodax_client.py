import httpx
import pytest

from app.clients.indodax_client import IndodaxClient


@pytest.fixture
def client():
    return IndodaxClient(
        api_key="test-api-key",
        secret_key="test-secret",
        base_url="https://example.test/",
        recv_window=5000,
    )


def test_get_account_sends_expected_request(
    client, monkeypatch
):
    monkeypatch.setattr(
        "app.clients.indodax_client.time.time",
        lambda: 123.456,
    )

    expected_data = {"balances": []}
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return httpx.Response(
            200,
            json=expected_data,
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(
        "app.clients.indodax_client.httpx.get",
        fake_get,
    )

    result = client.get_account()

    assert result == expected_data
    assert captured["url"] == (
        "https://example.test/api/v2/account"
    )
    assert captured["params"]["timestamp"] == 123456
    assert captured["params"]["recvWindow"] == 5000
    assert captured["params"]["omitZeroBalances"] == "false"
    assert captured["headers"]["X-APIKEY"] == "test-api-key"
    assert captured["headers"]["Accept"] == "application/json"
    assert len(captured["headers"]["Sign"]) == 64
    assert captured["timeout"] == 10.0


def test_get_open_orders_normalizes_symbol(
    client, monkeypatch
):
    monkeypatch.setattr(
        "app.clients.indodax_client.time.time",
        lambda: 123.456,
    )

    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return httpx.Response(
            200,
            json=[],
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(
        "app.clients.indodax_client.httpx.get",
        fake_get,
    )

    result = client.get_open_orders(" btcidr ")

    assert result == []
    assert captured["url"] == (
        "https://example.test/api/v2/openOrders"
    )
    assert captured["params"]["symbol"] == "BTCIDR"
    assert captured["params"]["timestamp"] == 123456
    assert captured["headers"]["X-APIKEY"] == "test-api-key"


@pytest.mark.parametrize(
    "symbol",
    ["", "BTC-IDR", "BTC IDR", "!"],
)
def test_get_open_orders_rejects_invalid_symbol(
    client, symbol
):
    with pytest.raises(ValueError, match="Invalid symbol format"):
        client.get_open_orders(symbol)



def test_get_open_orders_rejects_unexpected_response(
    client, monkeypatch
):
    def fake_get(url, **kwargs):
        return httpx.Response(
            200,
            json="unexpected",
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(
        "app.clients.indodax_client.httpx.get",
        fake_get,
    )

    with pytest.raises(
        ValueError,
        match="Unexpected open orders response format",
    ):
        client.get_open_orders()


def test_get_account_raises_on_http_error(
    client, monkeypatch
):
    response = httpx.Response(
        401,
        text="Unauthorized",
        request=httpx.Request(
            "GET",
            "https://example.test/api/v2/account",
        ),
    )

    monkeypatch.setattr(
        "app.clients.indodax_client.httpx.get",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(httpx.HTTPStatusError):
        client.get_account()

def test_order_history_supports_time_filters(client, monkeypatch):
    captured = {}

    def fake_signed_get(endpoint, params):
        captured["endpoint"] = endpoint
        captured["params"] = params
        return {"data": []}

    monkeypatch.setattr(client, "_signed_get", fake_signed_get)

    result = client.get_order_history(
        "btcidr",
        limit=50,
        start_time=1792500000000,
        end_time=1792586400000,
        sort="asc",
    )

    assert result == {"data": []}
    assert captured["endpoint"] == "/api/v2/order/histories"
    assert captured["params"]["symbol"] == "BTCIDR"
    assert captured["params"]["limit"] == 50
    assert captured["params"]["sort"] == "asc"
    assert captured["params"]["startTime"] == 1792500000000
    assert captured["params"]["endTime"] == 1792586400000


def test_trade_history_supports_client_order_id(client, monkeypatch):
    captured = {}

    def fake_signed_get(endpoint, params):
        captured["endpoint"] = endpoint
        captured["params"] = params
        return {"data": []}

    monkeypatch.setattr(client, "_signed_get", fake_signed_get)

    client.get_trade_history(
        "btcidr",
        client_order_id="test-client-123",
    )

    assert captured["endpoint"] == "/api/v2/myTrades"
    assert captured["params"]["clientOrderId"] == "test-client-123"


def test_history_rejects_range_over_seven_days(client):
    with pytest.raises(ValueError, match="7 days"):
        client.get_order_history(
            "BTCIDR",
            start_time=1000,
            end_time=1000 + 8 * 24 * 60 * 60 * 1000,
        )


def test_signed_params_does_not_mutate_input(client):
    original = {"symbol": "BTCIDR"}

    result = client._build_signed_params(original)

    assert original == {"symbol": "BTCIDR"}
    assert "timestamp" in result
    assert "recvWindow" in result

def test_history_endpoints_use_sha256(client, monkeypatch):
    captured = []

    def fake_get(url, **kwargs):
        captured.append((url, kwargs))

        return httpx.Response(
            200,
            json={"data": []},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(
        "app.clients.indodax_client.httpx.get",
        fake_get,
    )

    client.get_order_history("BTCIDR", limit=10)
    client.get_trade_history("BTCIDR", limit=10)

    assert len(captured) == 2

    for url, kwargs in captured:
        assert url.startswith("https://example.test/api/v2/")
        assert len(kwargs["headers"]["Sign"]) == 64
        assert kwargs["headers"]["X-APIKEY"] == "test-api-key"
        assert kwargs["headers"]["Accept"] == "application/json"