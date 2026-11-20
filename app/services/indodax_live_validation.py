from decimal import Decimal, InvalidOperation

import httpx


PUBLIC_URL = "https://indodax.com"


def positive_decimal(value, field):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Invalid " + field)

    if not number.is_finite() or number <= 0:
        raise ValueError("Invalid " + field)

    return number


def validate_order_response(result, order, client_order_id):
    if not isinstance(result, dict):
        raise ValueError("Invalid exchange response")

    if "code" in result or "msg" in result:
        raise ValueError("Exchange returned an error response")

    required = (
        "orderId", "clientOrderId", "symbol",
        "side", "type", "price", "origQty"
    )

    if any(result.get(key) is None for key in required):
        raise ValueError("Incomplete order response")

    order_id = result["orderId"]

    if (
        isinstance(order_id, bool)
        or not str(order_id).isdigit()
        or int(order_id) <= 0
    ):
        raise ValueError("Invalid exchange order ID")

    if result["clientOrderId"] != client_order_id:
        raise ValueError("Client order ID mismatch")

    if result["symbol"].upper() != order["symbol"].upper():
        raise ValueError("Symbol mismatch")

    if result["side"].upper() != order["side"].upper():
        raise ValueError("Side mismatch")

    if result["type"].upper() != "LIMIT":
        raise ValueError("Order type mismatch")

    if positive_decimal(result["price"], "price") != Decimal(
        str(order["price"])
    ):
        raise ValueError("Price mismatch")

    if positive_decimal(result["origQty"], "quantity") != Decimal(
        str(order["quantity"])
    ):
        raise ValueError("Quantity mismatch")

    return {
        "orderId": int(order_id),
        "clientOrderId": client_order_id,
        "symbol": order["symbol"],
        "accepted": True,
    }


def validate_cancel_response(result, symbol, order_id):
    if not isinstance(result, dict):
        raise ValueError("Invalid cancel response")

    if "code" in result or "msg" in result:
        raise ValueError("Exchange returned an error response")

    if (
        str(result.get("orderId")) != str(order_id)
        or str(result.get("symbol", "")).upper() != symbol.upper()
    ):
        raise ValueError("Cancel response identity mismatch")

    return {
        "orderId": str(order_id),
        "symbol": symbol.upper(),
        "cancel_acknowledged": True,
    }


def get_pair_rules(symbol):
    symbol = symbol.upper()

    with httpx.Client(timeout=10, trust_env=False) as client:
        response = client.get(PUBLIC_URL + "/api/pairs")
        response.raise_for_status()
        pairs = response.json()

        increments_response = client.get(
            PUBLIC_URL + "/api/price_increments"
        )
        increments_response.raise_for_status()
        increments = increments_response.json()["increments"]

    if not isinstance(pairs, list):
        raise ValueError("Invalid pairs response")

    pair = next(
        (
            item for item in pairs
            if item.get("symbol", "").upper() == symbol
        ),
        None
    )

    if pair is None:
        raise ValueError("Trading pair not found")

    pair_id = pair["id"].lower()
    ticker_id = pair.get("ticker_id", pair_id)

    if pair.get("is_maintenance") or pair.get("is_market_suspended"):
        raise PermissionError("Market is unavailable")

    return {
        "symbol": symbol,
        "base_asset": pair["traded_currency"].upper(),
        "quote_asset": pair["base_currency"].upper(),
        "min_notional": str(pair["trade_min_base_currency"]),
        "min_quantity": str(pair["trade_min_traded_currency"]),
        "quantity_increment": str(pair["quantity_increment"]),
        "price_increment": str(increments[ticker_id]),
    }


def validate_market_rules(order, rules):
    quantity = positive_decimal(order["quantity"], "quantity")
    price = positive_decimal(order["price"], "price")
    notional = quantity * price

    min_notional = positive_decimal(
        rules["min_notional"], "min_notional"
    )
    min_quantity = positive_decimal(
        rules["min_quantity"], "min_quantity"
    )
    quantity_step = positive_decimal(
        rules["quantity_increment"], "quantity_increment"
    )
    price_step = positive_decimal(
        rules["price_increment"], "price_increment"
    )

    if quantity < min_quantity:
        raise ValueError("Quantity below exchange minimum")

    if notional < min_notional:
        raise ValueError("Notional below exchange minimum")

    if quantity % quantity_step != 0:
        raise ValueError("Invalid quantity increment")

    if price % price_step != 0:
        raise ValueError("Invalid price increment")

    return {
        "notional_idr": str(notional),
        "min_notional_idr": str(min_notional),
        "min_quantity": str(min_quantity),
        "market_rules_valid": True,
    }


def validate_available_balance(account, order, rules):
    if not isinstance(account, dict):
        raise ValueError("Invalid account response")

    if account.get("canTrade") is not True:
        raise PermissionError("API key cannot trade")

    balances = account.get("balances")

    if not isinstance(balances, list):
        raise ValueError("Invalid balances response")

    side = order["side"].upper()

    asset = (
        rules["quote_asset"]
        if side == "BUY"
        else rules["base_asset"]
    )

    required = (
        Decimal(str(order["quantity"])) * Decimal(str(order["price"]))
        if side == "BUY"
        else Decimal(str(order["quantity"]))
    )

    matching = [
        item for item in balances
        if isinstance(item, dict)
        and str(item.get("asset", "")).upper() == asset
    ]

    if len(matching) > 1:
        raise ValueError("Duplicate asset balances")

    available = Decimal("0")

    if matching:
        raw_free = matching[0].get("free")
        if raw_free is None:
            raise ValueError("Missing free balance")

        available = Decimal(str(raw_free))

    if not available.is_finite() or available < 0:
        raise ValueError("Invalid free balance")

    if available < required:
        raise PermissionError(
            "Insufficient available balance for " + asset
        )

    return {
        "asset": asset,
        "available": str(available),
        "required_excluding_fees": str(required),
        "balance_check": "PASSED",
    }