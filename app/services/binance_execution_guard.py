import os
import re
from decimal import Decimal, InvalidOperation


class BinanceExecutionGuard:
    def __init__(self):
        self.enabled = (
            os.getenv("BINANCE_ENABLE_LIVE_TRADING", "false")
            .lower() == "true"
        )

        self.max_notional = Decimal(
            os.getenv("BINANCE_MAX_ORDER_NOTIONAL_USDT", "10")
        )

        if (
            not self.max_notional.is_finite()
            or self.max_notional <= 0
        ):
            raise ValueError("Invalid maximum order notional")

    def validate(self, symbol, side, quantity, price):
        symbol = str(symbol).upper()
        side = str(side).upper()

        if not re.fullmatch(r"[A-Z0-9]+USDT", symbol):
            raise ValueError("Only valid USDT pairs are supported")

        if side not in {"BUY", "SELL"}:
            raise ValueError("Invalid order side")

        try:
            quantity = Decimal(str(quantity))
            price = Decimal(str(price))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError("Invalid quantity or price")

        if not quantity.is_finite() or not price.is_finite():
            raise ValueError("Non-finite quantity or price")

        if quantity <= 0 or price <= 0:
            raise ValueError(
                "Quantity and price must be positive"
            )

        notional = quantity * price

        if notional > self.max_notional:
            raise PermissionError(
                "Order exceeds configured notional limit"
            )

        return {
            "symbol": symbol,
            "side": side,
            "quantity": str(quantity),
            "price": str(price),
            "notional_usdt": str(notional),
        }

    def require_live_enabled(self):
        if not self.enabled:
            raise PermissionError(
                "Live trading is disabled."
            )