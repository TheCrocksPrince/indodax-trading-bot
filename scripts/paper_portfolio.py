
import argparse
from decimal import Decimal, InvalidOperation

from app.clients.indodax_market_data import IndodaxMarketDataClient
from app.clients.paper_trading import PaperTradingEngine
from app.clients.paper_trade_store import PaperTradeStore
from app.clients.portfolio_engine import calculate_portfolio


# Saldo awal virtual. Sesuaikan dengan modal simulasi yang kamu inginkan.
# Saldo ini bukan saldo akun Indodax sungguhan.
INITIAL_BALANCES = {
    "IDR": Decimal("100000000"),
    "BTC": Decimal("0"),
}

DEFAULT_SYMBOL = "btcidr"
DEFAULT_FEE_RATE = "0.001"


def decimal_value(value, field_name):
    """Konversi angka ke Decimal dengan validasi sederhana."""
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("{} harus berupa angka yang valid".format(field_name))

    if not result.is_finite():
        raise ValueError("{} harus berupa angka finite".format(field_name))

    return result


def get_trade_details(record):
    """PaperTradeStore menyimpan detail transaksi di dalam key 'details'."""
    return record.get("details", record)


def reconstruct_balances(trades, initial_balances):
    """
    Rekonstruksi saldo virtual dengan memutar ulang riwayat paper trade.

    BUY:
      base bertambah sebesar quantity
      quote berkurang sebesar notional + fee

    SELL:
      base berkurang sebesar quantity
      quote bertambah sebesar notional - fee
    """
    balances = {
        asset.upper(): decimal_value(amount, "initial balance")
        for asset, amount in initial_balances.items()
    }

    for record in reversed(trades):
        trade = get_trade_details(record)

        side = str(trade.get("side", "")).upper()
        base = str(trade.get("base_asset", "")).upper()
        quote = str(trade.get("quote_asset", "")).upper()

        quantity = decimal_value(trade.get("quantity"), "quantity")
        notional = decimal_value(trade.get("notional"), "notional")
        fee = decimal_value(trade.get("fee", "0"), "fee")

        if side not in ("BUY", "SELL"):
            raise ValueError("Side transaksi harus BUY atau SELL")

        if not base or not quote or base == quote:
            raise ValueError("Base/quote asset tidak valid")

        balances.setdefault(base, Decimal("0"))
        balances.setdefault(quote, Decimal("0"))

        if side == "BUY":
            balances[base] += quantity
            balances[quote] -= notional + fee
        else:
            balances[base] -= quantity
            balances[quote] += notional - fee

    return balances


def fetch_market_prices(market_client, trades):
    """
    Ambil harga ticker terakhir untuk setiap pasangan yang masih punya posisi.
    Misalnya BTCIDR -> pair_id btcidr.
    """
    symbols = set()

    for record in trades:
        trade = get_trade_details(record)
        base = str(trade.get("base_asset", "")).upper()
        quote = str(trade.get("quote_asset", "")).upper()

        if base and quote and base != quote:
            symbols.add("{}{}".format(base, quote))

    prices = {}

    for symbol in sorted(symbols):
        ticker_response = market_client.get_ticker(symbol.lower())
        ticker = ticker_response.get("ticker", ticker_response)

        if "last" not in ticker:
            raise ValueError(
                "Ticker tidak memiliki harga 'last' untuk {}".format(symbol)
            )

        prices[symbol] = decimal_value(
            ticker["last"], "market price {}".format(symbol)
        )

    return prices


def print_report(report, balances):
    print("\n========== PAPER TRADING PORTFOLIO ==========")
    print("Jumlah transaksi tersimpan :", report["trade_count"])
    print("\n--- Saldo virtual ---")

    for asset in sorted(balances):
        print("{}: {}".format(asset, balances[asset]))

    print("\n--- Posisi aset ---")

    if not report["positions"]:
        print("Belum ada transaksi paper trading.")
    else:
        for symbol, position in sorted(report["positions"].items()):
            print("\n{}".format(symbol))
            print("  Quantity       :", position["quantity"])
            print("  Average cost   :", position["average_cost"])
            print("  Cost basis     :", position["cost_basis"])
            print("  Market price   :", position["market_price"])
            print("  Market value   :", position["market_value"])
            print("  Realized P/L   :", position["realized_pnl"])
            print("  Unrealized P/L :", position["unrealized_pnl"])

    print("\n--- Ringkasan ---")
    print("Total market value :", report["total_market_value"])
    print("Total cost basis   :", report["total_cost_basis"])
    print("Realized P/L       :", report["total_realized_pnl"])
    print("Unrealized P/L     :", report["total_unrealized_pnl"])
    print("Total P/L           :", report["total_pnl"])
    print("=============================================\n")


def main():
    
    parser = argparse.ArgumentParser(
        description="Paper trading portfolio report; tidak membuat live order."
    )

    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "--paper-buy-quantity",
        help="Simulasikan pembelian BTC dengan quantity tertentu.",
    )
    action_group.add_argument(
        "--paper-sell-quantity",
        help="Simulasikan penjualan BTC dengan quantity tertentu.",
    )

    parser.add_argument(
        "--db",
        default="data/paper_trading.db",
        help="Lokasi database SQLite paper trading.",
    )
    args = parser.parse_args()

    store = PaperTradeStore(db_path=args.db)
    market_client = IndodaxMarketDataClient()

    # Ambil seluruh riwayat. list_trades mengurutkan terbaru lebih dulu.
    # Rekonstruksi saldo dan portfolio perlu urutan kronologis, sehingga
    # reconstruct_balances membalik urutan tersebut sebelum memutarnya.
    trades = store.list_trades(limit=100000)

    
    if (
        args.paper_buy_quantity is not None
        or args.paper_sell_quantity is not None
    ):
        is_buy = args.paper_buy_quantity is not None

        raw_quantity = (
            args.paper_buy_quantity
            if is_buy
            else args.paper_sell_quantity
        )

        quantity = decimal_value(
            raw_quantity,
            "paper trade quantity",
        )

        if quantity <= Decimal("0"):
            parser.error("Quantity harus lebih besar dari nol")

        pair_id = DEFAULT_SYMBOL
        order_book = market_client.get_order_book(pair_id)

        balances = reconstruct_balances(trades, INITIAL_BALANCES)

        if not is_buy:
            available_btc = balances.get("BTC", Decimal("0"))

            if quantity > available_btc:
                parser.error(
                    "Quantity SELL melebihi saldo BTC virtual. "
                    "Tersedia: {}".format(available_btc)
                )

        engine = PaperTradingEngine(
            initial_balances=balances,
            fee_rate=DEFAULT_FEE_RATE,
        )

        if is_buy:
            trade = engine.buy_market(
                base_asset="BTC",
                quote_asset="IDR",
                quantity=quantity,
                order_book=order_book,
            )
        else:
            trade = engine.sell_market(
                base_asset="BTC",
                quote_asset="IDR",
                quantity=quantity,
                order_book=order_book,
            )

        store.save_trade(trade)

        action = "BUY" if is_buy else "SELL"
        print(
            "Paper {} berhasil disimulasikan dan disimpan.".format(action)
        )
        print("Tidak ada order yang dikirim ke Indodax.")

        trades = store.list_trades(limit=100000)

    balances = reconstruct_balances(trades, INITIAL_BALANCES)
    prices = fetch_market_prices(market_client, trades)
    report = calculate_portfolio(trades, prices)

    print_report(report, balances)


if __name__ == "__main__":
    main()
