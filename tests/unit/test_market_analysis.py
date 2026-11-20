
from decimal import Decimal

import pytest

from app.clients.market_analysis import (
    analyze_order_book,
    normalize_order_book,
)


def test_calculate_spread():
    book = {
        "buy": [[100, "2.0"], [99, "5.0"]],
        "sell": [[110, "3.0"], [111, "4.0"]],
    }

    result = analyze_order_book(book)

    assert result["best_bid"] == Decimal("100")
    assert result["best_ask"] == Decimal("110")
    assert result["spread"] == Decimal("10")
    assert result["spread_pct"] == Decimal("10") * Decimal("100") / Decimal("110")
    assert result["book_is_crossed"] is False
    assert result["book_is_locked"] is False


def test_best_prices_do_not_depend_on_response_order():
    book = {
        "buy": [[99, "1"], [101, "2"]],
        "sell": [[112, "1"], [110, "3"]],
    }

    result = analyze_order_book(book)

    assert result["best_bid"] == Decimal("101")
    assert result["best_ask"] == Decimal("110")


def test_empty_order_book_raises_error():
    with pytest.raises(ValueError):
        analyze_order_book({"buy": [], "sell": [[110, "1"]]})


def test_invalid_level_raises_error():
    with pytest.raises(ValueError):
        normalize_order_book({
            "buy": [["not-a-price", "1"]],
            "sell": [[110, "1"]],
        })


def test_crossed_order_book_is_flagged():
    result = analyze_order_book({
        "buy": [[112, "1"]],
        "sell": [[110, "1"]],
    })

    assert result["book_is_crossed"] is True
