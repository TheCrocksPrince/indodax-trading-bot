
import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from pathlib import Path

import httpx

from app.clients.binance_testnet_client import BinanceTestnetClient


SYMBOL = "BTCUSDT"
JOURNAL = Path("data/binance_cancel_journal.jsonl")


def record(event, **fields):
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    with JOURNAL.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry) + "\n")


def floor_step(value, step):
    return (value / step).to_integral_value(
        rounding=ROUND_DOWN
    ) * step


def main():
    client = BinanceTestnetClient()
    client_id = "bot_" + uuid.uuid4().hex[:20]
    submitted = False

    try:
        if client.BASE_URL != "https://testnet.binance.vision":
            raise RuntimeError("Testnet only")

        info = client.get_exchange_info(SYMBOL)
        rules = info["symbols"][0]
        if rules["status"] != "TRADING":
            raise RuntimeError("Symbol not trading")

        filters = {
            item["filterType"]: item
            for item in rules["filters"]
        }

        pf = filters["PRICE_FILTER"]
        lf = filters["LOT_SIZE"]
        nf = filters.get("NOTIONAL") or filters.get(
            "MIN_NOTIONAL"
        )

        ticker = client.get_book_ticker(SYMBOL)
        bid = Decimal(ticker["bidPrice"])
        ask = Decimal(ticker["askPrice"])
        tick = Decimal(pf["tickSize"])
        step = Decimal(lf["stepSize"])

        if bid <= 0 or ask <= 0 or bid >= ask:
            raise RuntimeError("Invalid Testnet order book")

        # Target below bid to reduce immediate execution risk
        price = floor_step(bid * Decimal("0.80"), tick)

        if not (
            Decimal(pf["minPrice"])
            <= price
            <= Decimal(pf["maxPrice"])
        ):
            raise RuntimeError("Price outside PRICE_FILTER")

        if price >= ask:
            raise RuntimeError("Price would cross the ask")

        if nf is None:
            raise RuntimeError("Missing notional filter")

        min_notional = Decimal(nf["minNotional"])
        max_notional = Decimal(
            nf.get("maxNotional", "0")
        )

        # Aim for at least 20% above minimum notional
        target = min_notional * Decimal("1.20")
        qty = (
            target / price / step
        ).to_integral_value(rounding="ROUND_CEILING") * step

        if not (
            Decimal(lf["minQty"])
            <= qty
            <= Decimal(lf["maxQty"])
        ):
            raise RuntimeError("Quantity outside LOT_SIZE")

        notional = price * qty

        if notional < min_notional:
            raise RuntimeError("Notional too small")

        if max_notional > 0 and notional > max_notional:
            raise RuntimeError("Notional too large")

        print("=== BINANCE CANCEL TEST ===")
        print("Best bid:", bid)
        print("Best ask:", ask)
        print("Limit BUY price:", price)
        print("Quantity:", qty)
        print("Notional:", notional)
        print("Client order ID:", client_id)

        record(
            "PREPARED",
            client_order_id=client_id,
            symbol=SYMBOL,
            price=str(price),
            quantity=str(qty),
        )

        if os.getenv("BINANCE_ENABLE_TESTNET_ORDERS") != "true":
            print("DRY RUN: no order submitted")
            return

        if input("Type CONFIRM TESTNET CANCEL: ") != (
            "CONFIRM TESTNET CANCEL"
        ):
            print("Cancelled before submission")
            return

        # Persist identifier before any potentially ambiguous POST
        record("SUBMITTING", client_order_id=client_id)
        submitted = True

        created = client.create_limit_order(
            SYMBOL,
            "BUY",
            str(qty),
            str(price),
            client_id,
        )

        record(
            "CREATED",
            client_order_id=client_id,
            order_id=created.get("orderId"),
            status=created.get("status"),
        )
        print("Created:", created.get("status"))

        order = client.get_order_by_client_id(
            SYMBOL, client_id
        )
        print("Queried:", order.get("status"))

        if order.get("status") in ("NEW", "PARTIALLY_FILLED"):
            record("CANCEL_SUBMITTING", client_order_id=client_id)
            cancelled = client.cancel_order_by_client_id(
                SYMBOL, client_id
            )
            record(
                "CANCEL_RESPONSE",
                client_order_id=client_id,
                status=cancelled.get("status"),
            )
            print("Cancel response:", cancelled.get("status"))

        final = client.get_order_by_client_id(
            SYMBOL, client_id
        )
        record(
            "FINAL",
            client_order_id=client_id,
            status=final.get("status"),
            executed_qty=final.get("executedQty"),
        )

        print("Final status:", final.get("status"))
        print("Executed quantity:", final.get("executedQty"))

        if final.get("status") == "CANCELED":
            print("CANCEL ORDER: PASS")
        else:
            print("CANCEL ORDER: NOT VERIFIED AS CANCELED")

    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        record(
            "RECONCILIATION_REQUIRED" if submitted else "ERROR",
            client_order_id=client_id,
            error_type=type(exc).__name__,
        )
        print("Request failed:", type(exc).__name__)
        if isinstance(exc, httpx.HTTPStatusError):
            print("HTTP:", exc.response.status_code)
            try:
                err = exc.response.json()
                print("Code:", err.get("code"))
                print("Message:", err.get("msg"))
            except (ValueError, AttributeError):
                pass
        if submitted:
            print("Check order by client ID before retrying.")
            print("Client order ID:", client_id)

    finally:
        client.close()


if __name__ == "__main__":
    main()
