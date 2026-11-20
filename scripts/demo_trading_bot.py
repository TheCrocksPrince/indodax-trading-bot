
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from app.clients.paper_trading import PaperTradingEngine
from app.clients.paper_trade_store import PaperTradeStore
from app.clients.portfolio_engine import calculate_portfolio
from app.strategies.strategy_engine import SpreadFilterStrategy
from app.strategies.risk_manager import RiskManager


def run_demo():
    print("=" * 55)
    print("INDODAX TRADING BOT — END-TO-END PAPER DEMO")
    print("MODE: SIMULATION ONLY")
    print("=" * 55)

    initial_idr = Decimal("1000000")

    engine = PaperTradingEngine(
        initial_balances={
            "IDR": initial_idr,
            "BTC": Decimal("0"),
        },
        fee_rate="0.001",
    )

    strategy = SpreadFilterStrategy(
        max_spread_pct="0.5",
        max_order_notional="100000",
        max_quantity="0.01",
    )

    risk_manager = RiskManager(
        max_position_notional="100000",
        max_daily_loss="50000",
        cooldown_seconds=0,
    )

    # Simulated market data.
    # The strategy expects "buy" and "sell" book sides.
    buy_book = {
        "buy": [
            ["999000000", "0.01"],
            ["998000000", "0.02"],
        ],
        "sell": [
            ["1000000000", "0.01"],
            ["1001000000", "0.02"],
        ],
    }

    sell_book = {
        "buy": [
            ["1001000000", "0.01"],
            ["1000000000", "0.02"],
        ],
        "sell": [
            ["1002000000", "0.01"],
            ["1003000000", "0.02"],
        ],
    }

    quantity = Decimal("0.00005")

    with TemporaryDirectory(prefix="indodax_demo_") as tmp:
        db_path = str(Path(tmp) / "paper_trading.db")
        store = PaperTradeStore(db_path=db_path)

        for side, book in (
            ("BUY", buy_book),
            ("SELL", sell_book),
        ):
            print("\n--- {} SIGNAL ---".format(side))

            result = strategy.execute_paper(
                engine=engine,
                order_book=book,
                base_asset="BTC",
                quote_asset="IDR",
                quantity=quantity,
                risk_manager=risk_manager,
                signal=side,
            )

            print("Decision:", result["decision"]["action"])
            print("Reason:", result["decision"]["reason"])

            if not result["executed"]:
                raise RuntimeError(
                    "{} paper trade was not executed".format(side)
                )

            trade = result["trade"]
            trade_id = store.save_trade(trade)

            print("Paper trade ID:", trade_id)
            print("Quantity:", trade["quantity"])
            print("Average price:", trade["average_price"])
            print("Notional:", trade["notional"])
            print("Fee:", trade["fee"])

        saved_trades = store.list_trades(limit=100)

        portfolio = calculate_portfolio(
            trades=saved_trades,
            market_prices={"BTCIDR": "1001000000"},
        )

        print("\n=== FINAL VIRTUAL BALANCES ===")
        print("IDR:", engine.balances["IDR"])
        print("BTC:", engine.balances["BTC"])

        print("\n=== PORTFOLIO SUMMARY ===")
        print("Trade count:", portfolio["trade_count"])
        print("Realized P/L:", portfolio["total_realized_pnl"])
        print("Unrealized P/L:", portfolio["total_unrealized_pnl"])
        print("Total P/L:", portfolio["total_pnl"])

        assert portfolio["trade_count"] == 2
        assert engine.balances["BTC"] == Decimal("0")
        assert portfolio["total_unrealized_pnl"] == 0

        # Cash balance must reconcile with realized P/L
        # after closing the entire BTC position.
        assert (
            engine.balances["IDR"] - initial_idr
            == portfolio["total_realized_pnl"]
        )

        print("\nEND-TO-END DEMO: PASSED")
        print("No live orders or withdrawals were sent.")

        return portfolio


if __name__ == "__main__":
    run_demo()
