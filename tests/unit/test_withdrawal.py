
import pytest

from app.clients.indodax_client import IndodaxClient


@pytest.fixture
def client():
    return IndodaxClient(
        api_key="test-key",
        secret_key="test-secret",
        base_url="https://example.test",
    )


def test_coin_withdrawal_dry_run(client):
    result = client.withdraw_coin(
        coin="USDT",
        network="TRC20",
        address="TExampleWallet123",
        amount="10.00000000",
        withdraw_order_id="withdraw123",
    )

    assert result["dry_run"] is True
    assert result["request_sent"] is False
    assert result["method"] == "POST"
    assert result["endpoint"] == (
        "/api/v2/capital/withdraw/apply"
    )


def test_idr_withdrawal_dry_run(client):
    result = client.withdraw_idr(
        amount=1000000,
        account_number="8760673466",
        bank_code="014",
        client_request_id="withdraw123",
    )

    assert result["dry_run"] is True
    assert result["request_sent"] is False
    assert result["params"]["currency"] == "IDR"
    assert result["params"]["accountInfo"]["bankCodeForPix"] == "014"


def test_coin_withdrawal_live_blocked(client):
    with pytest.raises(RuntimeError, match="disabled"):
        client.withdraw_coin(
            coin="BTC",
            network="BTC",
            address="TestWallet123",
            amount="1.0",
            withdraw_order_id="withdraw123",
            dry_run=False,
        )


def test_idr_withdrawal_live_blocked(client):
    with pytest.raises(RuntimeError, match="disabled"):
        client.withdraw_idr(
            amount=1000000,
            account_number="8760673466",
            bank_code="014",
            dry_run=False,
        )


@pytest.mark.parametrize(
    "amount",
    ["0", "-1", "abc", "NaN", "Infinity"],
)
def test_invalid_coin_amount(client, amount):
    with pytest.raises(ValueError):
        client.withdraw_coin(
            coin="BTC",
            network="BTC",
            address="TestWallet123",
            amount=amount,
            withdraw_order_id="withdraw123",
        )


def test_invalid_bank_code(client):
    with pytest.raises(ValueError):
        client.withdraw_idr(
            amount=1000000,
            account_number="8760673466",
            bank_code="14",
        )


def test_invalid_withdraw_username(client):
    with pytest.raises(ValueError):
        client.withdraw_coin(
            coin="BTC",
            network="BTC",
            address="TestWallet123",
            amount="1.0",
            withdraw_order_id="withdraw123",
            withdraw_method="username",
            withdraw_username="abc",
        )

