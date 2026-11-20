
import argparse
from decimal import Decimal, InvalidOperation
from pprint import pprint

from app.clients.indodax_client import create_indodax_client


def positive_decimal(value):
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise argparse.ArgumentTypeError("Invalid decimal value")

    if not number.is_finite() or number <= 0:
        raise argparse.ArgumentTypeError(
            "Value must be positive and finite"
        )

    return number


def main():
    parser = argparse.ArgumentParser(
        description="Create a live Indodax LIMIT order"
    )
    parser.add_argument("--symbol", required=True)
    parser.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL"],
    )
    parser.add_argument(
        "--price",
        required=True,
        type=positive_decimal,
    )
    parser.add_argument(
        "--quantity",
        required=True,
        type=positive_decimal,
    )
    args = parser.parse_args()

    symbol = args.symbol.strip().upper()
    if not symbol.isalnum():
        parser.error("Invalid symbol")

    client = create_indodax_client()

    notional = args.price * args.quantity

    print("\n=== INDODAX LIVE CREATE ORDER ===")
    print("Symbol:", symbol)
    print("Side:", args.side)
    print("Type: LIMIT")
    print("Price:", args.price)
    print("Quantity:", args.quantity)
    print("Estimated notional (excluding fees):", notional)
    print("Time in Force: GTC")

    # Build and validate the request locally first.
    preview = client.create_order(
        symbol=symbol,
        side=args.side,
        price=str(args.price),
        quantity=str(args.quantity),
        time_in_force="GTC",
        dry_run=True,
    )

    print("\n[1] Dry-run preview:")
    pprint(preview)

    print(
        "\nWARNING: This will place a REAL order. "
        "It may execute immediately or partially."
    )

    confirmation = input(
        "\nType CREATE to submit the live order: "
    )

    if confirmation != "CREATE":
        print("Aborted. No live order sent.")
        return

    print("\n[2] Submitting live order...")

    try:
        result = client.create_order(
            symbol=symbol,
            side=args.side,
            price=str(args.price),
            quantity=str(args.quantity),
            time_in_force="GTC",
            dry_run=False,
        )
    except Exception as exc:
        print("\nRequest failed or outcome is uncertain:")
        print(type(exc).__name__, str(exc))
        print(
            "Do not retry automatically. "
            "Check open orders and balances first."
        )
        return

    print("\n[3] Create Order API response:")
    pprint(result)

    order_id = (
        result.get("orderId")
        if isinstance(result, dict)
        else None
    )

    if order_id is not None:
        print("\nCreated Order ID:", order_id)
    else:
        print(
            "\nNo orderId found at top level. "
            "Inspect the response before proceeding."
        )

    print("\n[4] Checking open orders...")

    try:
        open_orders = client.get_open_orders(symbol)
        pprint(open_orders)
    except Exception as exc:
        print("Open orders verification failed:", str(exc))

    print("\nLive create request completed.")
    print(
        "An order absent from Open Orders may have "
        "filled, been rejected, or become inactive."
    )


if __name__ == "__main__":
    main()
