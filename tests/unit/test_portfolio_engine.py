
from decimal import Decimal

import pytest

from app.clients.portfolio_engine import calculate_portfolio


def make_trade(side, quantity, notional, fee):
    return {
        "side": side,
        "base_asset": "BTC",
        "quote_asset": "IDR",
        "quantity": Decimal(quantity),
        "notional": Decimal(notional),
        "fee": Decimal(fee),
    }


def test_buy_calculates_market_value_and_unrealized_pnl():
    trades = [
        make_trade("BUY", "2", "200", "2"),
    ]

    result = calculate_portfolio(
        trades,
        {"BTCIDR": "120"},
    )

    position = result["positions"]["BTCIDR"]

    assert position["quantity"] == Decimal("2")
    assert position["cost_basis"] == Decimal("202")
    assert position["market_value"] == Decimal("240")
    assert position["unrealized_pnl"] == Decimal("38")
    assert result["total_realized_pnl"] == Decimal("0")
    assert result["total_pnl"] == Decimal("38")


def test_weighted_average_cost_and_partial_sell():
    trades = [
        make_trade("BUY", "2", "200", "2"),
        make_trade("BUY", "1", "130", "1"),
        make_trade("SELL", "1", "140", "1"),
    ]

    result = calculate_portfolio(
        trades,
        {"BTCIDR": "120"},
    )

    position = result["positions"]["BTCIDR"]

    # Total buy cost = 202 + 131 = 333.
    # Weighted average cost = 333 / 3 = 111.
    # Realized P/L = (140 - 1) - 111 = 28.
    assert position["quantity"] == Decimal("2")
    assert position["cost_basis"] == Decimal("222")
    assert position["realized_pnl"] == Decimal("28")
    assert position["market_value"] == Decimal("240")
    assert position["unrealized_pnl"] == Decimal("18")
    assert result["total_pnl"] == Decimal("46")


def test_selling_entire_position_resets_remaining_cost_basis():
    trades = [
        make_trade("BUY", "1", "100", "0"),
        make_trade("SELL", "1", "120", "2"),
    ]

    result = calculate_portfolio(
        trades,
        {},
    )

    position = result["positions"]["BTCIDR"]

    assert position["quantity"] == Decimal("0")
    assert position["cost_basis"] == Decimal("0")
    assert position["realized_pnl"] == Decimal("18")
    assert result["total_unrealized_pnl"] == Decimal("0")
    assert result["total_pnl"] == Decimal("18")


def test_sell_more_than_holdings_is_rejected():
    trades = [
        make_trade("BUY", "1", "100", "0"),
        make_trade("SELL", "2", "200", "0"),
    ]

    with pytest.raises(ValueError, match="exceeds"):
        calculate_portfolio(trades, {})


def test_missing_market_price_is_rejected():
    trades = [
        make_trade("BUY", "1", "100", "0"),
    ]

    with pytest.raises(ValueError, match="Missing market price"):
        calculate_portfolio(trades, {})


def test_zero_quantity_is_rejected():
    trades = [
        make_trade("BUY", "0", "100", "0"),
    ]

    with pytest.raises(ValueError, match="quantity must be positive"):
        calculate_portfolio(trades, {"BTCIDR": "100"})


def test_negative_quantity_is_rejected():
    trades = [
        make_trade("BUY", "-1", "100", "0"),
    ]

    with pytest.raises(ValueError, match="quantity must be positive"):
        calculate_portfolio(trades, {"BTCIDR": "100"})


def test_negative_fee_is_rejected():
    trades = [
        make_trade("BUY", "1", "100", "-1"),
    ]

    with pytest.raises(
        ValueError,
        match="notional and fee cannot be negative",
    ):
        calculate_portfolio(trades, {"BTCIDR": "100"})


def test_negative_notional_is_rejected():
    trades = [
        make_trade("BUY", "1", "-100", "0"),
    ]

    with pytest.raises(
        ValueError,
        match="notional and fee cannot be negative",
    ):
        calculate_portfolio(trades, {"BTCIDR": "100"})


def test_negative_market_price_is_rejected():
    trades = [
        make_trade("BUY", "1", "100", "0"),
    ]

    with pytest.raises(
        ValueError,
        match="market price cannot be negative",
    ):
        calculate_portfolio(trades, {"BTCIDR": "-1"})
