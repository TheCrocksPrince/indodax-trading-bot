
from decimal import Decimal, InvalidOperation


ZERO = Decimal("0")


def _decimal(value, field_name):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("{} must be a valid number".format(field_name))

    if not result.is_finite():
        raise ValueError("{} must be finite".format(field_name))

    return result


def calculate_portfolio(trades, market_prices):
    """
    Calculate portfolio holdings and P/L from paper-trade history.

    Trades can be raw paper trades or rows returned by PaperTradeStore.
    market_prices maps symbols such as BTCIDR to current market prices.

    Buy fees are included in acquisition cost.
    Sell fees are deducted from sale proceeds.
    Cost basis uses the weighted-average method.
    """

    # PaperTradeStore menyimpan transaksi terbaru lebih dahulu.
    # Urutkan berdasarkan ID SQLite agar transaksi diproses kronologis.
    trades = list(trades)

    if trades and all(
        isinstance(record, dict) and "id" in record
        for record in trades
    ):
        trades.sort(key=lambda record: int(record["id"]))

    holdings = {}
    realized_pnl = {}
    trade_count = 0

    for record in trades:
        trade = record.get("details", record)

        side = str(trade.get("side", "")).upper()
        base = str(trade.get("base_asset", "")).upper()
        quote = str(trade.get("quote_asset", "")).upper()

        if side not in ("BUY", "SELL"):
            raise ValueError("Trade side must be BUY or SELL")
        if not base or not quote or base == quote:
            raise ValueError("Invalid base_asset or quote_asset")

        symbol = "{}{}".format(base, quote)
        quantity = _decimal(trade.get("quantity"), "quantity")
        notional = _decimal(trade.get("notional"), "notional")
        fee = _decimal(trade.get("fee", "0"), "fee")

        if quantity <= ZERO:
            raise ValueError("quantity must be positive")
        if notional < ZERO or fee < ZERO:
            raise ValueError("notional and fee cannot be negative")

        if symbol not in holdings:
            holdings[symbol] = {
                "base_asset": base,
                "quote_asset": quote,
                "quantity": ZERO,
                "cost_basis": ZERO,
            }
            realized_pnl[symbol] = ZERO

        position = holdings[symbol]

        if side == "BUY":
            acquisition_cost = notional + fee
            position["quantity"] += quantity
            position["cost_basis"] += acquisition_cost
        else:
            if quantity > position["quantity"]:
                raise ValueError(
                    "Sell quantity exceeds paper-trading holdings for {}".format(
                        symbol
                    )
                )

            average_cost = (
                position["cost_basis"] / position["quantity"]
                if position["quantity"] > ZERO
                else ZERO
            )
            cost_of_sold = average_cost * quantity
            net_proceeds = notional - fee

            realized_pnl[symbol] += net_proceeds - cost_of_sold
            position["quantity"] -= quantity
            position["cost_basis"] -= cost_of_sold

            if position["quantity"] == ZERO:
                position["cost_basis"] = ZERO

        trade_count += 1

    portfolio = {}
    total_market_value = ZERO
    total_cost_basis = ZERO
    total_unrealized_pnl = ZERO
    total_realized_pnl = ZERO

    for symbol, position in holdings.items():
        quantity = position["quantity"]
        cost_basis = position["cost_basis"]
        pnl_realized = realized_pnl[symbol]

        if quantity > ZERO:
            if symbol not in market_prices:
                raise ValueError(
                    "Missing market price for {}".format(symbol)
                )

            market_price = _decimal(
                market_prices[symbol], "market price"
            )
            if market_price < ZERO:
                raise ValueError("market price cannot be negative")

            market_value = quantity * market_price
            unrealized_pnl = market_value - cost_basis
            average_cost = cost_basis / quantity

        else:
            market_price = ZERO
            market_value = ZERO
            unrealized_pnl = ZERO
            average_cost = ZERO

        portfolio[symbol] = {
            "base_asset": position["base_asset"],
            "quote_asset": position["quote_asset"],
            "quantity": quantity,
            "average_cost": average_cost,
            "cost_basis": cost_basis,
            "market_price": market_price,
            "market_value": market_value,
            "realized_pnl": pnl_realized,
            "unrealized_pnl": unrealized_pnl,
        }

        total_market_value += market_value
        total_cost_basis += cost_basis
        total_unrealized_pnl += unrealized_pnl
        total_realized_pnl += pnl_realized

    return {
        "trade_count": trade_count,
        "positions": portfolio,
        "total_market_value": total_market_value,
        "total_cost_basis": total_cost_basis,
        "total_realized_pnl": total_realized_pnl,
        "total_unrealized_pnl": total_unrealized_pnl,
        "total_pnl": total_realized_pnl + total_unrealized_pnl,
    }
