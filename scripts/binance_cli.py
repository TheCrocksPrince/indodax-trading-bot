
import argparse
import json
import os
import sys
import httpx
from decimal import Decimal

from app.clients.binance_client import BinanceClient


def make_client(environment):
    if environment == "production":
        return BinanceClient(
            base_url="https://api.binance.com"
        )

    from app.clients.binance_testnet_client import (
        BinanceTestnetClient,
    )

    return BinanceTestnetClient()


def display(value, as_json=False):
    if as_json:
        print(json.dumps(value, indent=2, default=str))
        return

    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                print(f"{key}: {json.dumps(item, default=str)}")
            else:
                print(f"{key}: {item}")
        return

    if isinstance(value, list):
        if not value:
            print("No records found.")
            return

        for index, item in enumerate(value, 1):
            print(f"\n--- Record {index} ---")
            display(item)
        return

    print(value)


def get_account(client, as_json):
    account = client.get_account()

    # Avoid printing account identifiers and balances by default
    if as_json:
        print(
            "Full account JSON is disabled to protect "
            "sensitive information."
        )
        return

    summary = {
        "Account Type": account.get("accountType"),
        "Can Trade": account.get("canTrade"),
        "Can Withdraw": account.get("canWithdraw"),
        "Can Deposit": account.get("canDeposit"),
        "Balances": len(account.get("balances", [])),
    }

    display(summary)


def get_open_orders(client, symbol, as_json):
    orders = client.get_open_orders(symbol)

    if not isinstance(orders, list):
        raise ValueError("Unexpected open orders response")

    print(f"Open Orders: {len(orders)}")
    display(orders, as_json)


def get_order_history(client, symbol, as_json):
    orders = client.get_all_orders(symbol)

    if not isinstance(orders, list):
        raise ValueError("Unexpected order history response")

    print(f"Order History: {len(orders)}")
    display(orders, as_json)


def get_trades(client, symbol, as_json):
    trades = client.get_my_trades(symbol)

    if not isinstance(trades, list):
        raise ValueError("Unexpected trades response")

    print(f"My Trades: {len(trades)}")
    display(trades, as_json)


def cancel_testnet_order(client, symbol, order_id):
    if os.getenv("BINANCE_ENABLE_TESTNET_ORDERS") != "true":
        raise PermissionError(
            "Testnet cancellation is disabled. "
            "Set BINANCE_ENABLE_TESTNET_ORDERS=true "
            "to enable it."
        )

    print("Environment: TESTNET")
    print("Action: CANCEL ORDER")
    print(f"Symbol: {symbol}")
    print(f"Order ID: {order_id}")

    confirmation = input(
        "Type CANCEL TESTNET to continue: "
    )

    if confirmation != "CANCEL TESTNET":
        print("Cancelled by user. No request sent.")
        return

    # This assumes the existing testnet client exposes
    # cancel_order(symbol=..., order_id=...).
    result = client.cancel_order(
        symbol=symbol,
        order_id=order_id,
    )

    print("\nCancel response:")
    display(result)

    # Verify final status using the existing testnet query method.
    verified = client.get_order(
        symbol=symbol,
        order_id=order_id,
    )

    print("\nVerified order status:")
    display({
        "symbol": verified.get("symbol"),
        "orderId": verified.get("orderId"),
        "status": verified.get("status"),
    })

    if verified.get("status") != "CANCELED":
        raise RuntimeError(
            "Cancellation was not verified as CANCELED"
        )

    print("\nTESTNET CANCEL: PASS")


def main():
    parser = argparse.ArgumentParser(
        description="Binance Trading Bot CLI"
    )

    parser.add_argument(
        "command",
        choices=[
            "account",
            "open-orders",
            "order-history",
            "trades",
            "cancel-order",
        ],
    )

    parser.add_argument(
        "--env",
        choices=["production", "testnet"],
        default="production",
    )

    parser.add_argument(
        "--symbol",
        default="BTCUSDT",
    )

    parser.add_argument(
        "--order-id",
        type=int,
    )

    parser.add_argument(
        "--json",
        action="store_true",
    )

    args = parser.parse_args()
    symbol = args.symbol.upper()

    if args.command == "cancel-order":
        if args.env != "testnet":
            parser.error(
                "Cancel order is only available on TESTNET"
            )

        if args.order_id is None or args.order_id <= 0:
            parser.error(
                "A positive --order-id is required"
            )

    print("=== Binance Trading Bot CLI ===")
    print("Environment:", args.env.upper())
    print("Command:", args.command)
    print()

    client = make_client(args.env)

    if args.command == "account":
        get_account(client, args.json)

    elif args.command == "open-orders":
        get_open_orders(client, symbol, args.json)

    elif args.command == "order-history":
        get_order_history(client, symbol, args.json)

    elif args.command == "trades":
        get_trades(client, symbol, args.json)

    elif args.command == "cancel-order":
        cancel_testnet_order(
            client,
            symbol,
            args.order_id,
        )


if __name__ == "__main__":
    try:
        main()

    except httpx.HTTPStatusError as exc:
        response = exc.response

        print("CLI FAILED: HTTPStatusError")
        print("HTTP Status:", response.status_code)

        # Only expose Binance's error code, not request URLs
        # or authentication headers.
        try:
            payload = response.json()
            if isinstance(payload, dict):
                print("Binance Error Code:", payload.get("code"))
                print("Binance Message:", payload.get("msg"))
        except ValueError:
            print("Binance response was not JSON")

        sys.exit(1)

    except Exception as exc:
        print(
            f"CLI FAILED: {type(exc).__name__}",
            file=sys.stderr,
        )
        sys.exit(1)
