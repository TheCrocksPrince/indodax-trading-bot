
import json
from unittest.mock import MagicMock, patch

import pytest

from app.clients.indodax_client import IndodaxClient
from app.clients.withdrawal_journal import WithdrawalJournal

@pytest.fixture(autouse=True)
def isolated_withdrawal_journal(tmp_path):
    db_path = str(tmp_path / "withdrawal_test.db")

    def journal_factory():
        return WithdrawalJournal(db_path=db_path)

    with patch(
        "app.clients.indodax_client.WithdrawalJournal",
        side_effect=journal_factory,
    ):
        yield
        
@pytest.fixture
def client():
    # Bypass constructor to avoid loading real credentials.
    client = object.__new__(IndodaxClient)
    client.base_url = "https://example.test"

    client.signer = MagicMock()
    client.signer.sign.return_value = "test-signature"

    client._build_signed_params = MagicMock(
        side_effect=lambda params: {
            **params,
            "timestamp": 123456789,
            "recvWindow": 5000,
        }
    )
    client._build_headers = MagicMock(
        return_value={
            "X-APIKEY": "test-key",
            "Sign": "test-signature",
        }
    )
    return client


@pytest.fixture
def crypto_params():
    return {
        "coin": "BTC",
        "network": "BTC",
        "address": "test-address",
        "amount": "0.001",
        "withdraw_order_id": "testwithdraw001",
    }


@pytest.fixture
def idr_params():
    return {
        "amount": 200000,
        "account_number": "0012345678",
        "bank_code": "014",
        "client_request_id": "testidr001",
    }


def test_crypto_dry_run_never_sends(client, crypto_params):
    with patch("app.clients.indodax_client.httpx.post") as post:
        result = client.withdraw_coin(**crypto_params)

    assert result["request_sent"] is False
    assert result["dry_run"] is True
    post.assert_not_called()


def test_idr_dry_run_never_sends(client, idr_params):
    with patch("app.clients.indodax_client.httpx.post") as post:
        result = client.withdraw_idr(**idr_params)

    assert result["request_sent"] is False
    assert result["dry_run"] is True
    post.assert_not_called()


def test_crypto_live_disabled(
    client, crypto_params, monkeypatch
):
    monkeypatch.setenv(
        "INDODAX_ENABLE_LIVE_WITHDRAWAL", "false"
    )

    with patch("app.clients.indodax_client.httpx.post") as post:
        with pytest.raises(RuntimeError):
            client.withdraw_coin(
                **crypto_params, dry_run=False
            )

    post.assert_not_called()


def test_idr_live_disabled(
    client, idr_params, monkeypatch
):
    monkeypatch.setenv(
        "INDODAX_ENABLE_LIVE_WITHDRAWAL", "false"
    )

    with patch("app.clients.indodax_client.httpx.post") as post:
        with pytest.raises(RuntimeError):
            client.withdraw_idr(
                **idr_params, dry_run=False
            )

    post.assert_not_called()


def test_crypto_non_allowlisted_rejected(
    client, crypto_params, monkeypatch
):
    monkeypatch.setenv(
        "INDODAX_ENABLE_LIVE_WITHDRAWAL", "true"
    )
    monkeypatch.setenv(
        "INDODAX_WITHDRAW_ALLOWLIST", "[]"
    )

    with patch("app.clients.indodax_client.httpx.post") as post:
        with pytest.raises(PermissionError):
            client.withdraw_coin(
                **crypto_params, dry_run=False
            )

    post.assert_not_called()


def test_idr_non_allowlisted_rejected(
    client, idr_params, monkeypatch
):
    monkeypatch.setenv(
        "INDODAX_ENABLE_LIVE_WITHDRAWAL", "true"
    )
    monkeypatch.setenv(
        "INDODAX_IDR_WITHDRAW_ALLOWLIST", "[]"
    )

    with patch("app.clients.indodax_client.httpx.post") as post:
        with pytest.raises(PermissionError):
            client.withdraw_idr(
                **idr_params, dry_run=False
            )

    post.assert_not_called()


def test_crypto_live_mocked_request(
    client, crypto_params, monkeypatch
):
    monkeypatch.setenv(
        "INDODAX_ENABLE_LIVE_WITHDRAWAL", "true"
    )
    monkeypatch.setenv(
        "INDODAX_WITHDRAW_ALLOWLIST",
        json.dumps([{
            "coin": "BTC",
            "network": "BTC",
            "address": "test-address",
        }])
    )

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "12345",
        "withdrawOrderId": "testwithdraw001",
    }

    with patch(
        "app.clients.indodax_client.httpx.post",
        return_value=mock_response,
    ) as post:
        result = client.withdraw_coin(
            **crypto_params, dry_run=False
        )

    assert result["id"] == "12345"
    post.assert_called_once()

    args, kwargs = post.call_args

    assert args[0].endswith(
        "/api/v2/capital/withdraw/apply"
    )
    assert kwargs["data"]["coin"] == "BTC"
    assert kwargs["data"]["withdrawOrderId"] == (
        "testwithdraw001"
    )
    assert kwargs["headers"]["Content-Type"] == (
        "application/x-www-form-urlencoded"
    )
    assert kwargs["follow_redirects"] is False
    mock_response.raise_for_status.assert_called_once()


def test_idr_live_mocked_request(
    client, idr_params, monkeypatch
):
    monkeypatch.setenv(
        "INDODAX_ENABLE_LIVE_WITHDRAWAL", "true"
    )
    monkeypatch.setenv(
        "INDODAX_IDR_WITHDRAW_ALLOWLIST",
        json.dumps([{
            "accountNumber": "0012345678",
            "bankCodeForPix": "014",
        }])
    )

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {"orderId": "test-order-123"}
    }

    with patch(
        "app.clients.indodax_client.httpx.post",
        return_value=mock_response,
    ) as post:
        result = client.withdraw_idr(
            **idr_params, dry_run=False
        )

    assert result["data"]["orderId"] == "test-order-123"
    post.assert_called_once()

    args, kwargs = post.call_args

    assert args[0].endswith("/api/v2/fiat/withdraw")
    assert kwargs["data"]["amount"] == 200000
    assert kwargs["data"]["clientRequestId"] == (
        "testidr001"
    )

    account_info = json.loads(
        kwargs["data"]["accountInfo"]
    )

    assert account_info == {
        "accountNumber": "0012345678",
        "bankCodeForPix": "014",
    }
    assert kwargs["headers"]["Content-Type"] == (
        "application/x-www-form-urlencoded"
    )
    mock_response.raise_for_status.assert_called_once()


@pytest.mark.parametrize(
    "amount",
    [100000, 1000000000],
)
def test_idr_amount_outside_limits(
    client, idr_params, amount
):
    idr_params["amount"] = amount

    with patch("app.clients.indodax_client.httpx.post") as post:
        with pytest.raises(ValueError):
            client.withdraw_idr(**idr_params)

    post.assert_not_called()
