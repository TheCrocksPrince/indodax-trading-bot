
import argparse
import json

from app.clients.indodax_market_data import IndodaxMarketDataClient


def main():
    parser = argparse.ArgumentParser(
        description="Read public Indodax market data"
    )
    parser.add_argument(
        "--pair",
        default="btcidr",
        help="Pair ID from /api/pairs, e.g. btcidr",
    )
    parser.add_argument(
        "--data",
        choices=["pairs", "ticker", "orderbook"],
        default="ticker",
        help="Market data type to retrieve",
    )
    args = parser.parse_args()

    client = IndodaxMarketDataClient()

    if args.data == "pairs":
        result = client.get_pairs()
    elif args.data == "ticker":
        result = client.get_ticker(args.pair)
    else:
        result = client.get_order_book(args.pair)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
