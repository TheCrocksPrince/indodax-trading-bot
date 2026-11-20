
from unittest.mock import patch

import httpx

from app.clients.indodax_client import IndodaxClient


client = IndodaxClient(
    api_key="demo-key",
    secret_key="demo-secret",
    base_url="https://example.test",
)

# In-memory simulated exchange state
orders = {}
next_order_id = 10001


def fake_post(url, **kwargs):
    global next_order_id

    order_id = next_order_id
    next_order_id += 1

    order = {
        "orderId": order_id,
        "symbol": "BTCIDR",
        "side": "BUY",
        "type": "LIMIT",
        "status": "NEW",
    }
    orders[order_id] = order

    return httpx.Response(
        200,
        json=order,
        request=httpx.Request("POST", url),
    )


def fake_get(url, **kwargs):
    symbol = kwargs.get("params", {}).get("symbol")
    active = [
        order
        for order in orders.values()
        if order["status"] == "NEW"
        and (symbol is None or order["symbol"] == symbol)
    ]

    return httpx.Response(
        200,
        json=active,
        request=httpx.Request("GET", url),
    )


def fake_delete(url, **kwargs):
    params = kwargs["params"]
    order_id = params["orderId"]

    order = orders.get(order_id)
    if order is None or order["status"] != "NEW":
        return httpx.Response(
            404,
            json={"error": "Order not found or not active"},
            request=httpx.Request("DELETE", url),
        )

    order["status"] = "CANCELED"

    return httpx.Response(
        200,
        json={
            "orderId": order_id,
            "symbol": order["symbol"],
            "status": "CANCELED",
        },
        request=httpx.Request("DELETE", url),
    )


def main():
    with patch(
        "app.clients.indodax_client.httpx.post",
        side_effect=fake_post,
    ), patch(
        "app.clients.indodax_client.httpx.get",
        side_effect=fake_get,
    ), patch(
        "app.clients.indodax_client.httpx.delete",
        side_effect=fake_delete,
    ):
        print("=== LOCAL MOCK EXCHANGE DEMO ===")

        print("\n[1] CREATE LIMIT BUY ORDER")
        created = client.create_order(
            symbol="BTCIDR",
            side="BUY",
            price="1000000000",
            quantity="0.00001",
            dry_run=False,
        )
        print(created)
        assert created["status"] == "NEW"

        order_id = created["orderId"]

        print("\n[2] GET OPEN ORDERS")
        open_orders = client.get_open_orders("BTCIDR")
        print(open_orders)
        assert any(
            order["orderId"] == order_id
            for order in open_orders
        )

        print("\n[3] CANCEL ORDER")
        cancelled = client.cancel_order(
            symbol="BTCIDR",
            order_id=order_id,
            dry_run=False,
        )
        print(cancelled)
        assert cancelled["status"] == "CANCELED"

        print("\n[4] VERIFY OPEN ORDERS")
        remaining = client.get_open_orders("BTCIDR")
        print(remaining)
        assert not any(
            order["orderId"] == order_id
            for order in remaining
        )

        print("\nSUCCESS: CREATE -> OPEN -> CANCEL -> VERIFIED")
        print("No real exchange requests were sent.")


if __name__ == "__main__":
    main()
