
from decimal import Decimal

import pytest

from app.clients.paper_trading import PaperTradingEngine


@pytest.fixture
def order_book():
    return {
        "buy": [
            ["100", "2"],
            ["99", "3"],
        ],
        "sell": [
            ["101", "1"],
            ["102", "2"],
        ],
    }


def test_market_buy_updates_virtual_balances(order_book):
    engine = PaperTradingEngine(
        {"IDR": "1000", "BTC": "0"},
        fee_rate="0.01",
    )

    trade = engine.buy_market("BTC", "IDR", "1.5", order_book)

    # 1 BTC at 101, 0.5 BTC at 102.
    assert trade["notional"] == Decimal("152")
    assert trade["fee"] == Decimal("1.52")
    assert engine.balances["BTC"] == Decimal("1.5")
    assert engine.balances["IDR"] == Decimal("846.48")


def test_market_sell_updates_virtual_balances(order_book):
    engine = PaperTradingEngine(
        {"IDR": "0", "BTC": "2"},
        fee_rate="0.01",
    )

    trade = engine.sell_market("BTC", "IDR", "1.5", order_book)

    # 1.5 BTC sold at the best bid of 100.
    assert trade["notional"] == Decimal("150")
    assert trade["fee"] == Decimal("1.50")
    assert engine.balances["BTC"] == Decimal("0.5")
    assert engine.balances["IDR"] == Decimal("148.50")


def test_insufficient_balance_does_not_change_balances(order_book):
    engine = PaperTradingEngine(
        {"IDR": "10", "BTC": "0"},
        fee_rate="0.01",
    )
    before = engine.balances.copy()

    with pytest.raises(ValueError, match="Insufficient virtual quote"):
        engine.buy_market("BTC", "IDR", "1", order_book)

    assert engine.balances == before
    assert engine.trades == []


def test_insufficient_liquidity_does_not_change_balances(order_book):
    engine = PaperTradingEngine(
        {"IDR": "1000", "BTC": "0"},
        fee_rate="0",
    )
    before = engine.balances.copy()

    with pytest.raises(ValueError, match="Insufficient order book"):
        engine.buy_market("BTC", "IDR", "10", order_book)

    assert engine.balances == before
    assert engine.trades == []


def test_zero_quantity_is_rejected(order_book):
    engine = PaperTradingEngine({"IDR": "1000", "BTC": "0"})

    with pytest.raises(ValueError, match="quantity must be positive"):
        engine.buy_market("BTC", "IDR", "0", order_book)
