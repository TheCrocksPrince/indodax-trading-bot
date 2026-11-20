from unittest.mock import MagicMock, patch

from scripts.order_management import (
    withdraw_coin,
    withdraw_idr,
)


def test_crypto_withdrawal_live_confirmed():
    client = MagicMock()

    answers = iter([
        "ADDRESS",
        "BTC",
        "BTC",
        "test-wallet-address",
        "0.001",
        "testwithdraw001",
        "",
        "CONFIRM WITHDRAW COIN",
    ])

    with patch("builtins.input", side_effect=lambda _: next(answers)):
        withdraw_coin(client, live=True)

    client.withdraw_coin.assert_called_once()

    kwargs = client.withdraw_coin.call_args.kwargs

    assert kwargs["dry_run"] is False
    assert kwargs["coin"] == "BTC"
    assert kwargs["network"] == "BTC"
    assert kwargs["address"] == "test-wallet-address"
    assert kwargs["withdraw_order_id"] == "testwithdraw001"


def test_crypto_withdrawal_without_confirmation():
    client = MagicMock()

    answers = iter([
        "ADDRESS",
        "BTC",
        "BTC",
        "test-wallet-address",
        "0.001",
        "testwithdraw002",
        "",
        "NO",
    ])

    with patch("builtins.input", side_effect=lambda _: next(answers)):
        withdraw_coin(client, live=True)

    kwargs = client.withdraw_coin.call_args.kwargs

    assert kwargs["dry_run"] is True


def test_idr_withdrawal_live_confirmed():
    client = MagicMock()

    answers = iter([
        "200000",
        "0012345678",
        "014",
        "testidr001",
        "CONFIRM WITHDRAW IDR",
    ])

    with patch("builtins.input", side_effect=lambda _: next(answers)):
        withdraw_idr(client, live=True)

    kwargs = client.withdraw_idr.call_args.kwargs

    assert kwargs["dry_run"] is False
    assert kwargs["amount"] == 200000
    assert kwargs["account_number"] == "0012345678"
    assert kwargs["bank_code"] == "014"
    assert kwargs["client_request_id"] == "testidr001"


def test_idr_withdrawal_without_confirmation():
    client = MagicMock()

    answers = iter([
        "200000",
        "0012345678",
        "014",
        "testidr002",
        "NO",
    ])

    with patch("builtins.input", side_effect=lambda _: next(answers)):
        withdraw_idr(client, live=True)

    kwargs = client.withdraw_idr.call_args.kwargs

    assert kwargs["dry_run"] is True