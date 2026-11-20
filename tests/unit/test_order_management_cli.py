from unittest.mock import MagicMock

import pytest

from scripts import order_management as cli


@pytest.mark.parametrize(
    "side,order_type,values,expected",
    [
        (
            "BUY",
            "MARKET",
            ["BTCIDR", "BUY", "MARKET", "100000"],
            {"quote_order_qty": "100000"},
        ),
        (
            "SELL",
            "MARKET",
            ["BTCIDR", "SELL", "MARKET", "0.001"],
            {"quantity": "0.001"},
        ),
        (
            "BUY",
            "LIMIT",
            ["BTCIDR", "BUY", "LIMIT", "1000000000", "0.001"],
            {"price": "1000000000", "quantity": "0.001"},
        ),
    ],
)
def test_cli_create_order_dry_run(
    monkeypatch, side, order_type, values, expected
):
    inputs = iter(values)
    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(inputs),
    )

    client = MagicMock()
    client.create_order.return_value = {
        "mode": "DRY_RUN",
        "sent": False,
    }

    cli.create_order(client)

    kwargs = client.create_order.call_args.kwargs

    assert kwargs["side"] == side
    assert kwargs["order_type"] == order_type
    assert kwargs["dry_run"] is True

    for key, value in expected.items():
        assert kwargs[key] == value


def test_cli_cancel_always_dry_run(monkeypatch):
    inputs = iter(["BTCIDR", "12345"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(inputs),
    )

    client = MagicMock()
    client.cancel_order.return_value = {
        "mode": "DRY_RUN",
        "sent": False,
    }

    cli.cancel_order(client)

    kwargs = client.cancel_order.call_args.kwargs

    assert kwargs["symbol"] == "BTCIDR"
    assert kwargs["order_id"] == 12345
    assert kwargs["dry_run"] is True