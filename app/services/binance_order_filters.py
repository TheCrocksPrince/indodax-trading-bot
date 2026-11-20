from decimal import Decimal


def validate_limit_order_filters(order, exchange_info):
    symbols = exchange_info.get("symbols", [])

    symbol_info = next(
        (
            item for item in symbols
            if item.get("symbol") == order["symbol"]
        ),
        None,
    )

    if symbol_info is None:
        raise ValueError("Symbol not found on Binance")

    if symbol_info.get("status") != "TRADING":
        raise ValueError("Symbol is not trading")

    filters = {
        item["filterType"]: item
        for item in symbol_info.get("filters", [])
    }

    quantity = Decimal(order["quantity"])
    price = Decimal(order["price"])
    notional = quantity * price

    price_filter = filters.get("PRICE_FILTER")

    if price_filter:
        min_price = Decimal(price_filter["minPrice"])
        max_price = Decimal(price_filter["maxPrice"])
        tick_size = Decimal(price_filter["tickSize"])

        if min_price > 0 and price < min_price:
            raise ValueError("Price below minimum")

        if max_price > 0 and price > max_price:
            raise ValueError("Price above maximum")

        if tick_size > 0 and (
            price % tick_size != 0
        ):
            raise ValueError("Invalid price tick size")

    lot_size = filters.get("LOT_SIZE")

    if lot_size:
        min_qty = Decimal(lot_size["minQty"])
        max_qty = Decimal(lot_size["maxQty"])
        step_size = Decimal(lot_size["stepSize"])

        if quantity < min_qty or quantity > max_qty:
            raise ValueError("Quantity outside LOT_SIZE")

        if step_size > 0 and (
            quantity % step_size != 0
        ):
            raise ValueError("Invalid quantity step size")

    for filter_name in ("NOTIONAL", "MIN_NOTIONAL"):
        rule = filters.get(filter_name)

        if rule:
            min_notional = Decimal(
                rule.get("minNotional", "0")
            )

            if notional < min_notional:
                raise ValueError(
                    "Order below minimum notional"
                )

            max_notional = Decimal(
                rule.get("maxNotional", "0")
            )

            if max_notional > 0 and notional > max_notional:
                raise ValueError(
                    "Order above maximum notional"
                )

    return True