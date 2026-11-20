
import json
from decimal import Decimal

from app.clients.indodax_market_data import IndodaxMarketDataClient
from app.clients.paper_trading import PaperTradingEngine
from app.clients.paper_trade_store import PaperTradeStore


def json_default(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    raise TypeError("Unsupported type: {}".format(type(value).__name__))


def main():
    pair_id = "btcidr"
    quantity = Decimal("0.00001")

    # Saldo virtual untuk demonstrasi, bukan saldo akun sungguhan.
    engine = PaperTradingEngine(
        initial_balances={
            "IDR": "100000000",
            "BTC": "0",
        },
        fee_rate="0.001",
    )

    market = IndodaxMarketDataClient()
    order_book = market.get_order_book(pair_id)

    print("Balances before:")
    print(json.dumps(engine.balances, default=json_default, indent=2))

    trade = engine.buy_market(
        base_asset="BTC",
        quote_asset="IDR",
        quantity=quantity,
        order_book=order_book,
    )

    print("\nSimulated trade:")
    print(json.dumps(trade, default=json_default, indent=2))

    print("\nBalances after:")
    print(json.dumps(engine.balances, default=json_default, indent=2))


if __name__ == "__main__":
    main()
