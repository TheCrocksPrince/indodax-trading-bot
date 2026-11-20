
import pytest

from app.clients.indodax_client import IndodaxClient


@pytest.fixture
def client():
    return IndodaxClient(
        api_key="test-key",
        secret_key="test-secret",
        base_url="https://example.test",
    )


@pytest.fixture
def capture_request(client, monkeypatch):
    captured = {}

    def fake_signed_get(endpoint, params):
        captured["endpoint"] = endpoint
        captured["params"] = params
        return {"data": []}

    monkeypatch.setattr(client, "_signed_get", fake_signed_get)
    return captured


def test_withdraw_history(client, capture_request):
    client.get_coin_withdraw_history(
        coin="usdt",
        limit=50,
        status="success",
    )

    assert capture_request["endpoint"] == (
        "/api/v2/capital/withdraw/history"
    )
    assert capture_request["params"]["coin"] == "USDT"
    assert capture_request["params"]["WithdrawStatus"] == "success"


def test_deposit_history(client, capture_request):
    client.get_coin_deposit_history(
        coin="eth",
        status="pending",
    )

    assert capture_request["endpoint"] == (
        "/api/v2/capital/deposit/hisrec"
    )
    assert capture_request["params"]["coin"] == "ETH"
    assert capture_request["params"]["depositStatus"] == "pending"


def test_fiat_orders(client, capture_request):
    client.get_fiat_orders(transaction_type="0")

    assert capture_request["endpoint"] == "/api/v2/fiat/orders"
    assert capture_request["params"]["transactionType"] == "0"


def test_deposit_address_list(client, capture_request):
    client.get_deposit_address_list("usdt", "trc20")

    assert capture_request["endpoint"] == (
        "/api/v2/capital/deposit/address/list"
    )
    assert capture_request["params"]["coin"] == "USDT"
    assert capture_request["params"]["network"] == "trc20"


@pytest.mark.parametrize(
    "limit",
    [0, 9, 1001, True, 10.5],
)
def test_invalid_history_limit(client, limit):
    with pytest.raises(ValueError):
        client.get_coin_deposit_history(limit=limit)


def test_withdraw_history_rejects_over_90_days(client):
    with pytest.raises(ValueError, match="90 days"):
        client.get_coin_withdraw_history(
            start_time=1000,
            end_time=1000 + 91 * 86400000,
        )


def test_fiat_orders_rejects_over_30_days(client):
    with pytest.raises(ValueError, match="30 days"):
        client.get_fiat_orders(
            begin_time=1000,
            end_time=1000 + 31 * 86400000,
        )


def test_deposit_address_requires_network(client):
    with pytest.raises(ValueError):
        client.get_deposit_address_list("USDT", "")
