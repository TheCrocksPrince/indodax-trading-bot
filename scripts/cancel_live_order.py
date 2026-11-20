
import argparse
from pprint import pprint

from app.clients.indodax_client import create_indodax_client


def get_orders(response):
    if isinstance(response, list):
        return response

    if isinstance(response, dict):
        orders = response.get("orders")
        if isinstance(orders, list):
            return orders

    raise ValueError("Unexpected open orders response format")


def main():
    parser = argparse.ArgumentParser(
        description="Cancel an existing Indodax order"
    )
    parser.add_argument(
        "--symbol",
        required=True,
        help="Trading pair, e.g. MUBARAKIDR",
    )
    parser.add_argument(
        "--order-id",
        required=True,
        type=int,
        help="Order ID to cancel",
    )
    args = parser.parse_args()

    symbol = args.symbol.strip().upper()
    order_id = args.order_id

    if not symbol.isalnum() or order_id <= 0:
        raise ValueError("Invalid symbol or order ID")

    client = create_indodax_client()

    print("\n=== INDODAX CANCEL ORDER ===")
    print("Symbol:", symbol)
    print("Order ID:", order_id)

    # Step 1: Verify order exists
    print("\n[1] Fetching open orders...")
    orders = get_orders(client.get_open_orders(symbol))

    target = next(
        (
            order for order in orders
            if str(order.get("orderId")) == str(order_id)
            and str(order.get("symbol", "")).upper() == symbol
        ),
        None,
    )

    if target is None:
        print("Order not found in open orders.")
        print("No cancel request sent.")
        return

    print("\n[2] Order found:")
    pprint(target)

    # Step 2: Explicit confirmation
    confirmation = input(
        "\nType CANCEL to confirm live cancellation: "
    )

    if confirmation != "CANCEL":
        print("Cancellation aborted. No request sent.")
        return

    # Step 3: Send actual DELETE request
    print("\n[3] Sending cancel request...")

    try:
        result = client.cancel_order(
            symbol=symbol,
            order_id=order_id,
            dry_run=False,
        )
        print("\nCancel API response:")
        pprint(result)
    except Exception as exc:
        print("Cancel request failed or outcome is uncertain:")
        print(type(exc).__name__, str(exc))
        print("Check order status before retrying.")
        return

    # Step 4: Verify order is no longer open
    print("\n[4] Verifying open orders...")

    try:
        remaining = get_orders(client.get_open_orders(symbol))
    except Exception as exc:
        print("Verification failed:", str(exc))
        print("Cancellation status not yet confirmed.")
        return

    still_open = any(
        str(order.get("orderId")) == str(order_id)
        for order in remaining
    )

    if still_open:
        print("WARNING: Order still appears in open orders.")
    else:
        print("SUCCESS: Order is no longer in open orders.")
        print(
            "Note: This does not by itself distinguish "
            "cancellation from execution."
        )


if __name__ == "__main__":
    main()
