
from decimal import Decimal

from scripts.paper_portfolio import reconstruct_balances


def make_trade(side, quantity, notional, fee):
    return {
        "side": side,
        "base_asset": "BTC",
        "quote_asset": "IDR",
        "quantity": str(quantity),
        "notional": str(notional),
        "fee": str(fee),
    }


def test_reconstruct_balances_after_buy():
    # Riwayat dari PaperTradeStore diurutkan terbaru lebih dulu.
    trades = [
        {
            "details": make_trade("BUY", "0.1", "1000", "1")
        }
    ]

    balances = reconstruct_balances(
        trades,
        {"IDR": Decimal("10000"), "BTC": Decimal("0")},
    )

    assert balances["BTC"] == Decimal("0.1")
    assert balances["IDR"] == Decimal("8999")


def test_reconstruct_balances_after_buy_and_sell():
    # list_trades() mengembalikan SELL lebih dahulu, lalu BUY.
    trades = [
        {
            "details": make_trade("SELL", "0.04", "480", "0.48")
        },
        {
            "details": make_trade("BUY", "0.1", "1000", "1")
        },
    ]

    balances = reconstruct_balances(
        trades,
        {"IDR": Decimal("10000"), "BTC": Decimal("0")},
    )

    assert balances["BTC"] == Decimal("0.06")
    assert balances["IDR"] == Decimal("9478.52")
