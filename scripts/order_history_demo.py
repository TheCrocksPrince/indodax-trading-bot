
from pprint import pprint

from app.clients.indodax_client import create_indodax_client


def input_symbol():
    while True:
        symbol = input(
            "Enter trading pair (e.g. BTCIDR): "
        ).strip().upper()

        if symbol and symbol.isalnum():
            return symbol

        print("Invalid symbol. Please try again.")


def input_order_id():
    while True:
        value = input("Enter numeric Order ID: ").strip()

        if value.isdigit() and int(value) > 0:
            return int(value)

        print("Invalid Order ID. Please enter a positive number.")


def input_limit():
    while True:
        value = input(
            "Enter limit (10-1000, default 100): "
        ).strip()

        if not value:
            return 100

        if value.isdigit() and 10 <= int(value) <= 1000:
            return int(value)

        print("Limit must be between 10 and 1000.")


def main():
    print("\n=== INDODAX TRADE API V2 ===")
    print("1. Get Order Detail")
    print("2. Get Order History")
    print("3. Get My Trades")
    print("0. Exit")

    choice = input("\nChoose an option (0-3): ").strip()

    if choice == "0":
        print("Exiting.")
        return

    if choice not in ("1", "2", "3"):
        print("Invalid option.")
        return

    symbol = input_symbol()
    client = create_indodax_client()

    try:
        if choice == "1":
            order_id = input_order_id()

            print("\n=== ORDER DETAIL ===")
            result = client.get_order(
                symbol=symbol,
                order_id=order_id,
            )

        elif choice == "2":
            limit = input_limit()

            print("\n=== ORDER HISTORY ===")
            result = client.get_order_history(
                symbol=symbol,
                limit=limit,
            )

        else:
            limit = input_limit()

            print("\n=== MY TRADES ===")
            result = client.get_trade_history(
                symbol=symbol,
                limit=limit,
            )

        print("\nAPI Response:")
        pprint(result)

    except Exception as exc:
        print("\nRequest failed:")
        print(type(exc).__name__, str(exc))


if __name__ == "__main__":
    main()
