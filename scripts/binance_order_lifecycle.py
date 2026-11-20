
import os
import uuid
from decimal import Decimal

import httpx

from app.clients.binance_testnet_client import BinanceTestnetClient


SYMBOL = "BTCUSDT"
QUANTITY = "0.00010"
PRICE = "75000.00"


def main():
    client = BinanceTestnetClient()
    client_order_id = "bot_" + uuid.uuid4().hex[:20]

    print("=== BINANCE TESTNET ORDER LIFECYCLE ===")
    print("Symbol:", SYMBOL)
    print("Client order ID:", client_order_id)

    try:
        # Validate exchange rules before submitting
        info = client.get_exchange_info(SYMBOL)
        symbol_info = info["symbols"][0]

        if symbol_info["status"] != "TRADING":
            raise RuntimeError("Symbol is not trading")

        filters = {
            f["filterType"]: f
            for f in symbol_info["filters"]
        }

        price = Decimal(PRICE)
        quantity = Decimal(QUANTITY)
        notional = price * quantity

        price_filter = filters["PRICE_FILTER"]
        lot_filter = filters["LOT_SIZE"]
        notional_filter = filters.get("NOTIONAL")

        tick = Decimal(price_filter["tickSize"])
        step = Decimal(lot_filter["stepSize"])

        assert price > 0
        assert quantity > 0
        assert price % tick == 0
        assert quantity % step == 0
        assert Decimal(price_filter["minPrice"]) <= price
        assert price <= Decimal(price_filter["maxPrice"])
        assert Decimal(lot_filter["minQty"]) <= quantity
        assert quantity <= Decimal(lot_filter["maxQty"])

        if notional_filter:
            assert notional >= Decimal(
                notional_filter["minNotional"]
            )
            assert notional <= Decimal(
                notional_filter["maxNotional"]
            )

        print("VALIDATION: PASS")

        if os.getenv("BINANCE_ENABLE_TESTNET_ORDERS") != "true":
            print("ORDER SUBMISSION: DISABLED")
            print("Set BINANCE_ENABLE_TESTNET_ORDERS=true")
            return

        confirmation = input(
            "Type CONFIRM TESTNET ORDER: "
        )

        if confirmation != "CONFIRM TESTNET ORDER":
            print("CANCELLED BY USER")
            return

        # Create a real order on TESTNET only
        print("\n1. CREATE ORDER")

        try:
            created = client.create_limit_order(
                SYMBOL,
                "BUY",
                QUANTITY,
                PRICE,
                client_order_id,
            )
        except httpx.RequestError:
            print("CREATE RESULT UNKNOWN")
            print("Do not retry automatically.")
            print("Reconcile using client order ID.")
            raise

        print("Order ID:", created.get("orderId"))
        print("Status:", created.get("status"))

        # Query
        print("\n2. QUERY ORDER")

        order = client.get_order_by_client_id(
            SYMBOL,
            client_order_id,
        )

        print("Order status:", order.get("status"))
        print("Executed quantity:", order.get("executedQty"))

        # Cancel only if still open
        if order.get("status") in (
            "NEW",
            "PARTIALLY_FILLED",
        ):
            print("\n3. CANCEL ORDER")

            try:
                cancelled = client.cancel_order_by_client_id(
                    SYMBOL,
                    client_order_id,
                )
                print(
                    "Cancel response:",
                    cancelled.get("status"),
                )
            except (httpx.RequestError, httpx.HTTPStatusError):
                print("CANCEL RESULT UNKNOWN")
                print("Reconcile order before retrying.")

        # Verify final state
        print("\n4. VERIFY ORDER")

        final_order = client.get_order_by_client_id(
            SYMBOL,
            client_order_id,
        )

        print("Final status:", final_order.get("status"))
        print(
            "Executed quantity:",
            final_order.get("executedQty"),
        )

        print("\nORDER LIFECYCLE COMPLETED")

    except httpx.HTTPStatusError as exc:
        print("HTTP ERROR:", exc.response.status_code)
        try:
            error = exc.response.json()
            print("Code:", error.get("code"))
            print("Message:", error.get("msg"))
        except ValueError:
            print("Non-JSON error response")

    finally:
        client.close()


if __name__ == "__main__":
    main()
