
from decimal import Decimal

from app.clients.paper_trading import PaperTradingEngine
from app.clients.paper_trade_store import PaperTradeStore
from app.clients.portfolio_engine import calculate_portfolio
from scripts.paper_portfolio import reconstruct_balances


INITIAL_BALANCES = {
    "IDR": Decimal("10000"),
    "BTC": Decimal("0"),
}

ORDER_BOOK = {
    "buy": [["100", "10"]],
    "sell": [["101", "10"]],
}


def test_buy_sell_persistence_and_portfolio(tmp_path):
    db_path = str(tmp_path / "integration_test.db")
    store = PaperTradeStore(db_path=db_path)

    # 1. Simulasikan BUY menggunakan engine asli.
    engine = PaperTradingEngine(
        initial_balances=INITIAL_BALANCES.copy(),
        fee_rate="0.001",
    )

    buy_trade = engine.buy_market(
        base_asset="BTC",
        quote_asset="IDR",
        quantity=Decimal("0.1"),
        order_book=ORDER_BOOK,
    )
    store.save_trade(buy_trade)

    # 2. Muat ulang riwayat dari SQLite.
    trades = store.list_trades(limit=100)
    assert len(trades) == 1
    assert trades[0]["side"] == "BUY"

    # 3. Pulihkan saldo, lalu buat engine baru untuk SELL.
    balances = reconstruct_balances(trades, INITIAL_BALANCES)

    assert balances["BTC"] == Decimal("0.1")

    sell_engine = PaperTradingEngine(
        initial_balances=balances,
        fee_rate="0.001",
    )

    sell_trade = sell_engine.sell_market(
        base_asset="BTC",
        quote_asset="IDR",
        quantity=Decimal("0.04"),
        order_book=ORDER_BOOK,
    )
    store.save_trade(sell_trade)

    # 4. Pastikan kedua transaksi tersimpan.
    trades = store.list_trades(limit=100)
    assert len(trades) == 2

    # 5. Hitung kembali saldo dan portofolio.
    balances = reconstruct_balances(trades, INITIAL_BALANCES)
    report = calculate_portfolio(
        trades,
        {"BTCIDR": Decimal("100")},
    )

    position = report["positions"]["BTCIDR"]

    assert position["quantity"] == Decimal("0.06")
    assert balances["BTC"] == Decimal("0.06")
    assert position["realized_pnl"] == (
        Decimal(str(sell_trade["notional"]))
        - Decimal(str(sell_trade["fee"]))
        - (
            (
                Decimal(str(buy_trade["notional"]))
                + Decimal(str(buy_trade["fee"]))
            )
            / Decimal(str(buy_trade["quantity"]))
            * Decimal("0.04")
        )
    )
    assert report["trade_count"] == 2
    assert position["market_value"] == Decimal("6.00")


def test_multiple_buys_partial_sell_persist_weighted_average_cost(tmp_path):
    db_path = str(tmp_path / "weighted_average_test.db")
    store = PaperTradeStore(db_path=db_path)

    engine = PaperTradingEngine(
        initial_balances=INITIAL_BALANCES.copy(),
        fee_rate="0.001",
    )

    # BUY pertama: harga ask 101.
    buy_1 = engine.buy_market(
        base_asset="BTC",
        quote_asset="IDR",
        quantity=Decimal("0.1"),
        order_book={
            "buy": [["100", "10"]],
            "sell": [["101", "10"]],
        },
    )
    store.save_trade(buy_1)

    # BUY kedua: harga ask 111.
    buy_2 = engine.buy_market(
        base_asset="BTC",
        quote_asset="IDR",
        quantity=Decimal("0.1"),
        order_book={
            "buy": [["110", "10"]],
            "sell": [["111", "10"]],
        },
    )
    store.save_trade(buy_2)

    # Baca ulang riwayat sebelum membuat SELL.
    trades = store.list_trades(limit=100)
    assert len(trades) == 2

    balances = reconstruct_balances(trades, INITIAL_BALANCES)
    assert balances["BTC"] == Decimal("0.2")

    # Engine baru menggunakan saldo hasil pemulihan.
    sell_engine = PaperTradingEngine(
        initial_balances=balances,
        fee_rate="0.001",
    )

    # SELL sebagian: harga bid 120.
    sell = sell_engine.sell_market(
        base_asset="BTC",
        quote_asset="IDR",
        quantity=Decimal("0.05"),
        order_book={
            "buy": [["120", "10"]],
            "sell": [["121", "10"]],
        },
    )
    store.save_trade(sell)

    # Baca ulang semua transaksi dari SQLite.
    trades = store.list_trades(limit=100)
    assert len(trades) == 3

    balances = reconstruct_balances(trades, INITIAL_BALANCES)

    report = calculate_portfolio(
        trades,
        {"BTCIDR": Decimal("115")},
    )
    position = report["positions"]["BTCIDR"]

    # Dua BUY masing-masing 0.1 BTC, lalu SELL 0.05 BTC.
    assert position["quantity"] == Decimal("0.15")
    assert balances["BTC"] == Decimal("0.15")

    # Weighted average cost memasukkan biaya transaksi BUY.
    total_buy_cost = (
        Decimal(str(buy_1["notional"]))
        + Decimal(str(buy_1["fee"]))
        + Decimal(str(buy_2["notional"]))
        + Decimal(str(buy_2["fee"]))
    )
    total_buy_quantity = (
        Decimal(str(buy_1["quantity"]))
        + Decimal(str(buy_2["quantity"]))
    )
    average_cost = total_buy_cost / total_buy_quantity

    expected_realized_pnl = (
        Decimal(str(sell["notional"]))
        - Decimal(str(sell["fee"]))
        - average_cost * Decimal(str(sell["quantity"]))
    )

    assert position["realized_pnl"] == expected_realized_pnl
    assert report["trade_count"] == 3
    assert position["market_value"] == Decimal("17.25")
