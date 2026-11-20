
import json

from app.clients.indodax_market_data import IndodaxMarketDataClient
from app.clients.market_analysis import analyze_order_book


def decimal_to_string(value):
    if value is None:
        return None
    return format(value, "f")


def main():
    pair_id = "btcidr"
    client = IndodaxMarketDataClient()

    ticker = client.get_ticker(pair_id)
    order_book = client.get_order_book(pair_id)
    analysis = analyze_order_book(order_book)

    result = {
        "pair_id": pair_id,
        "ticker": {
            "last": ticker.get("last"),
            "buy": ticker.get("buy"),
            "sell": ticker.get("sell"),
            "server_time": ticker.get("server_time"),
        },
        "order_book_analysis": {
            key: decimal_to_string(value)
            if key in ("best_bid", "best_ask", "spread", "spread_pct")
            else value
            for key, value in analysis.items()
        },
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
