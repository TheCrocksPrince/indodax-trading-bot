
import argparse
import json

from app.clients.indodax_client import create_indodax_client


def main():
    parser = argparse.ArgumentParser(
        description="Read open orders from Indodax Trade API V2"
    )
    parser.add_argument(
        "--symbol",
        default=None,
        help="Optional trading pair, e.g. BTCIDR",
    )
    args = parser.parse_args()

    client = create_indodax_client()
    result = client.get_open_orders(args.symbol)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
