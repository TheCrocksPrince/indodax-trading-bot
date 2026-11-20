
import argparse
from pprint import pprint

from app.clients.indodax_market_data import IndodaxMarketDataClient
from app.clients.paper_trading import PaperTradingEngine
from app.strategies.strategy_engine import SpreadFilterStrategy
from app.strategies.risk_manager import RiskManager
from app.strategies.order_book_signal import OrderBookSignal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", default="btcidr")
    parser.add_argument(
        "--signal",
        choices=["AUTO", "BUY", "SELL", "HOLD"],
        default="AUTO",
    )
    parser.add_argument("--quantity", default="0.00001")
    parser.add_argument("--max-spread-pct", default="0.5")
    parser.add_argument("--max-notional", default="100000")
    args = parser.parse_args()

    if not args.pair.lower().endswith("idr"):
        parser.error("Demo currently supports IDR quote pairs only")

    base_asset = args.pair[:-3].upper()

    market_client = IndodaxMarketDataClient()
    order_book = market_client.get_order_book(args.pair)

    signal_result = None
    effective_signal = args.signal

    if args.signal == "AUTO":
        signal_result = OrderBookSignal(depth=5).generate(order_book)
        effective_signal = signal_result["signal"]

        print("\n=== AUTOMATED SIGNAL ===")
        pprint(signal_result)

    engine = PaperTradingEngine(
        initial_balances={
            "IDR": "1000000",
            base_asset: "1",
        },
        fee_rate="0.001",
    )

    strategy = SpreadFilterStrategy(
        max_spread_pct=args.max_spread_pct,
        max_order_notional=args.max_notional,
        max_quantity="1",
    )

    print("\n=== PAPER TRADING STRATEGY DEMO ===")
    print("Pair:", args.pair.upper())
    print("Signal:", args.signal)
    print("Quantity:", args.quantity)

    risk_manager = RiskManager(
    max_position_notional="100000",
    max_daily_loss="50000",
    cooldown_seconds=60,
)

    result = strategy.execute_paper(
        engine=engine,
        order_book=order_book,
        base_asset=base_asset,
        quote_asset="IDR",
        quantity=args.quantity,
        signal=effective_signal,
        risk_manager=risk_manager,
    )

    print("\nDecision:")
    pprint(result["decision"])

    print("\nPaper trade:")
    pprint(result["trade"])

    print("\nVirtual balances:")
    pprint(engine.balances)

    print("\nLIVE ORDERS SENT: 0")


if __name__ == "__main__":
    main()
