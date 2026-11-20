
from decimal import Decimal

import pytest

from app.strategies.order_book_signal import OrderBookSignal


def test_buy_signal():
    book = {
        "buy": [["100", "8"]],
        "sell": [["101", "2"]],
    }

    result = OrderBookSignal().generate(book)

    assert result["signal"] == "BUY"
    assert result["imbalance"] == Decimal("0.6")


def test_sell_signal():
    book = {
        "buy": [["100", "2"]],
        "sell": [["101", "8"]],
    }

    result = OrderBookSignal().generate(book)

    assert result["signal"] == "SELL"
    assert result["imbalance"] == Decimal("-0.6")


def test_hold_signal():
    book = {
        "buy": [["100", "5"]],
        "sell": [["101", "5"]],
    }

    result = OrderBookSignal().generate(book)

    assert result["signal"] == "HOLD"


def test_order_book_level_order_does_not_change_signal():
    book = {
        "buy": [["99", "2"], ["100", "8"]],
        "sell": [["102", "2"], ["101", "2"]],
    }

    result = OrderBookSignal(depth=1).generate(book)

    assert result["signal"] == "BUY"
    assert result["bid_volume"] == Decimal("8")
    assert result["ask_volume"] == Decimal("2")


def test_crossed_book_returns_hold():
    book = {
        "buy": [["102", "8"]],
        "sell": [["101", "2"]],
    }

    result = OrderBookSignal().generate(book)

    assert result["signal"] == "HOLD"
    assert "Crossed" in result["reason"]


def test_empty_book_returns_hold():
    book = {
        "buy": [],
        "sell": [["101", "2"]],
    }

    result = OrderBookSignal().generate(book)

    assert result["signal"] == "HOLD"


def test_invalid_depth():
    with pytest.raises(ValueError):
        OrderBookSignal(depth=0)


def test_invalid_threshold():
    with pytest.raises(ValueError):
        OrderBookSignal(
            buy_threshold="-0.3",
            sell_threshold="0.3",
        )
