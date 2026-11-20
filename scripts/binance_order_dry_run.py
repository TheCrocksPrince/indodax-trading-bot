import argparse
import json

from app.clients.binance_execution_client import BinanceExecutionClient


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--symbol", required=True)
    parser.add_argument("--side", choices=["BUY", "SELL"], required=True)
    parser.add_argument("--quantity", required=True)
    parser.add_argument("--price", required=True)

    args = parser.parse_args()

    execution = BinanceExecutionClient()

    result = execution.prepare_limit_order(
        symbol=args.symbol,
        side=args.side,
        quantity=args.quantity,
        price=args.price,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()