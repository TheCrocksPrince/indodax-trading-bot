
"""Indodax Trade API v2 CLI, Python 3.9+.

GET operations call the configured API. Mutations require an explicit
confirmation and delegate to IndodaxClient; client-level guards remain in force.
"""

import argparse
import json
from decimal import Decimal, InvalidOperation

import httpx

from app.clients.indodax_client import create_indodax_client


def display(label, result):
    print("\n=== {} ===".format(label))
    print(json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
        default=str
    ))


def ask(label, default=None, required=True):
    suffix = " [{}]".format(default) if default is not None else ""

    while True:
        value = input("{}{}: ".format(label, suffix)).strip()

        if value:
            return value

        if default is not None:
            return str(default)

        if not required:
            return None

        print("This field is required.")


def choose(label, options):
    options = tuple(options)

    while True:
        value = ask(
            "{} ({})".format(label, "/".join(options))
        ).upper()

        if value in options:
            return value

        print("Invalid choice.")


def positive(label, integer=False):
    while True:
        raw = ask(label)

        try:
            number = Decimal(raw)

            if not number.is_finite() or number <= 0:
                raise ValueError()

            if integer and number != number.to_integral_value():
                raise ValueError()

            return int(number) if integer else str(number)

        except (InvalidOperation, ValueError):
            print(
                "Enter a positive {}.".format(
                    "integer" if integer else "number"
                )
            )


def order_id():
    return positive("Order ID", integer=True)


def symbol():
    while True:
        value = ask(
            "Trading pair (e.g. BTCIDR)"
        ).upper()

        if value.isascii() and value.isalnum():
            return value

        print("Invalid trading pair.")


def limit():
    while True:
        value = ask(
            "Limit (10-1000)",
            default="100"
        )

        if value.isdigit() and 10 <= int(value) <= 1000:
            return int(value)

        print("Limit must be between 10 and 1000.")


def confirm_live(action, details, enabled):
    display("TRANSACTION PREVIEW", details)

    if not enabled:
        print(
            "DRY-RUN: No production mutation will be sent."
        )
        return False

    print(
        "WARNING: This can change real orders "
        "or transfer real funds."
    )

    expected = "CONFIRM {}".format(action)

    return input(
        "Type exactly {}: ".format(expected)
    ).strip() == expected


def create_order(client, live=False):
    pair = symbol()
    side = choose("Side", ("BUY", "SELL"))
    kind = choose(
        "Order type",
        ("LIMIT", "MARKET")
    )

    params = {
        "symbol": pair,
        "side": side,
        "order_type": kind
    }

    if kind == "LIMIT":
        params["price"] = positive("Limit price")
        params["quantity"] = positive("Quantity")

        params["time_in_force"] = "GTC"

        params["notional"] = str(
            Decimal(params["price"]) *
            Decimal(params["quantity"])
        )

    elif side == "BUY":
        params["quote_order_qty"] = str(positive(
            "IDR to spend",
            integer=True
        ))

    else:
        params["quantity"] = positive(
            "Quantity to sell"
        )

    preview = dict(params)
    params.pop("notional", None)

    approved = confirm_live(
        "CREATE",
        preview,
        live
    )

    display(
        "CREATE ORDER RESULT",
        client.create_order(
            dry_run=not approved,
            **params
        )
    )


def cancel_order(client, live=False):
    params = {
        "symbol": symbol(),
        "order_id": order_id()
    }

    approved = confirm_live(
        "CANCEL",
        params,
        live
    )

    display(
        "CANCEL ORDER RESULT",
        client.cancel_order(
            dry_run=not approved,
            **params
        )
    )


def withdraw_coin(client, live):
    method = choose(
        "Withdrawal method",
        ("ADDRESS", "USERNAME")
    ).lower()

    params = {
        "coin": ask("Coin").upper(),
        "network": ask(
            "Network",
            required=False
        ) or "",
        "address": ask("Withdrawal address"),
        "amount": positive("Amount"),
        "withdraw_order_id": ask(
            "Unique withdrawal order ID"
        ),
        "withdraw_method": method
    }

    tag = ask(
        "Address tag / memo",
        required=False
    )

    if tag:
        params["address_tag"] = tag

    if method == "username":
        params["withdraw_username"] = ask(
            "Withdrawal username"
        )

    preview = dict(params)

    address = params["address"]

    approved = confirm_live(
        "WITHDRAW COIN",
        preview,
        live
    )

    display(
        "CRYPTO WITHDRAWAL RESULT",
        client.withdraw_coin(
            dry_run=not approved,
            **params
        )
    )


def withdraw_idr(client, live):
    params = {
        "amount": positive(
            "IDR amount",
            integer=True
        ),
        "account_number": ask(
            "Bank account number"
        ),
        "bank_code": ask(
            "Bank code (3 digits)"
        )
    }

    request_id = ask(
        "Unique client request ID"
    )

    params["client_request_id"] = request_id

    preview = dict(params)

    approved = confirm_live(
        "WITHDRAW IDR",
        preview,
        live
    )

    display(
        "IDR WITHDRAWAL RESULT",
        client.withdraw_idr(
            dry_run=not approved,
            **params
        )
    )


def menu(live_mutations, live_withdrawals=False):
    print("\n=== INDODAX TRADE API V2 ===")
    print(
        "Trading mutations: {}".format(
            "LIVE ENABLED" if live_mutations else "DRY-RUN"
        )
    )
    print(
        "Withdrawals: {}".format(
            "LIVE CONFIRMATION ENABLED"
            if live_withdrawals else "DRY-RUN"
        )
    )

    options = (
        "GET Account",
        "GET Open Orders",
        "GET Order Detail",
        "GET Order History",
        "GET My Trades",
        "GET Crypto Withdrawal History",
        "GET Crypto Deposit History",
        "GET Fiat Orders",
        "GET Deposit Address List",
        "POST Create Order",
        "DELETE Cancel Order",
        "POST Crypto Withdrawal",
        "POST IDR Withdrawal",
    )

    for index, title in enumerate(options, 1):
        print("{:2d}. {}".format(index, title))

    print(" 0. Exit")


def main():
    parser = argparse.ArgumentParser(
        description="Indodax Trade API v2 CLI"
    )

    parser.add_argument(
        "--live-mutations",
        action="store_true",
        help=(
            "Request live mutation through existing "
            "client guards; each action requires confirmation"
        )
    )

    parser.add_argument(
        "--live-withdrawals",
        action="store_true",
        help="Enable withdrawal confirmation flow separately",
    )

    args = parser.parse_args()
    client = create_indodax_client()

    while True:
        menu(
            args.live_mutations,
            args.live_withdrawals,
        )

        try:
            choice = ask(
                "Choose option (0-13)"
            )

            if choice == "0":
                break

            if choice == "1":
                display(
                    "ACCOUNT",
                    client.get_account()
                )

            elif choice == "2":
                pair = ask(
                    "Trading pair (blank = all)",
                    required=False
                )

                display(
                    "OPEN ORDERS",
                    client.get_open_orders(
                        symbol=pair.upper() if pair else None
                    )
                )

            elif choice == "3":
                pair = symbol()
                oid = order_id()

                display(
                    "ORDER DETAIL",
                    client.get_order(pair, oid)
                )

            elif choice == "4":
                display(
                    "ORDER HISTORY",
                    client.get_order_history(
                        symbol(),
                        limit()
                    )
                )

            elif choice == "5":
                display(
                    "MY TRADES",
                    client.get_trade_history(
                        symbol(),
                        limit()
                    )
                )

            elif choice == "6":
                display(
                    "CRYPTO WITHDRAWAL HISTORY",
                    client.get_coin_withdraw_history(
                        coin=ask(
                            "Coin", "BTC"
                        ).upper(),
                        limit=limit()
                    )
                )

            elif choice == "7":
                display(
                    "CRYPTO DEPOSIT HISTORY",
                    client.get_coin_deposit_history(
                        coin=ask(
                            "Coin", "BTC"
                        ).upper(),
                        limit=limit()
                    )
                )

            elif choice == "8":
                display(
                    "FIAT ORDERS",
                    client.get_fiat_orders(
                        transaction_type=choose(
                            "Transaction type",
                            ("0", "1")
                        ),
                        limit=limit()
                    )
                )

            elif choice == "9":
                display(
                    "DEPOSIT ADDRESS LIST",
                    client.get_deposit_address_list(
                        coin=ask("Coin").upper(),
                        network=ask("Network").upper()
                    )
                )

            elif choice == "10":
                create_order(
                    client,
                    args.live_mutations
                )

            elif choice == "11":
                cancel_order(
                    client,
                    args.live_mutations
                )

            elif choice == "12":
                withdraw_coin(
                    client,
                    args.live_withdrawals
                )

            elif choice == "13":
                withdraw_idr(
                    client,
                    args.live_withdrawals
                )

            else:
                print("Invalid option.")

        except httpx.HTTPStatusError as exc:
            print(
                "HTTP status:",
                exc.response.status_code
            )

            try:
                display(
                    "API ERROR",
                    exc.response.json()
                )

            except ValueError:
                print(exc.response.text)

        except (
            ValueError,
            RuntimeError,
            httpx.RequestError,
            TypeError
        ) as exc:
            print(
                "Request failed: {}: {}".format(
                    type(exc).__name__,
                    exc
                )
            )

        except KeyboardInterrupt:
            print(
                "\nInterrupted; returning to menu."
            )

        except EOFError:
            break


if __name__ == "__main__":
    main()
