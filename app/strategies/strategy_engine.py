
from decimal import Decimal
from typing import Any, Dict

from app.clients.market_analysis import (
    analyze_order_book,
    normalize_order_book,
    to_decimal,
)
from app.clients.paper_trading import PaperTradingEngine

from app.strategies.risk_manager import RiskManager


class SpreadFilterStrategy:
    """
    Strategi demonstrasi berbasis spread dan sinyal eksplisit.

    Tidak menghasilkan prediksi arah harga.
    Tidak pernah mengirim live order.
    """

    def __init__(
        self,
        max_spread_pct: Any = "0.5",
        max_order_notional: Any = "100000",
        max_quantity: Any = "1",
    ):
        self.max_spread_pct = to_decimal(max_spread_pct)
        self.max_order_notional = to_decimal(max_order_notional)
        self.max_quantity = to_decimal(max_quantity)

        if self.max_spread_pct < 0:
            raise ValueError("max_spread_pct cannot be negative")

        if self.max_order_notional <= 0 or self.max_quantity <= 0:
            raise ValueError("Risk limits must be positive")

    def evaluate(
        self,
        order_book: Dict[str, Any],
        signal: str = "HOLD",
    ) -> Dict[str, Any]:
        signal = signal.strip().upper()

        if signal not in ("BUY", "SELL", "HOLD"):
            raise ValueError("Signal must be BUY, SELL, or HOLD")

        try:
            analysis = analyze_order_book(order_book)
        except ValueError as exc:
            return {
                "action": "HOLD",
                "reason": "Invalid market conditions: {}".format(exc),
                "analysis": None,
            }

        if analysis["book_is_crossed"] or analysis["book_is_locked"]:
            return {
                "action": "HOLD",
                "reason": "Crossed or locked order book",
                "analysis": analysis,
            }

        if analysis["spread_pct"] > self.max_spread_pct:
            return {
                "action": "HOLD",
                "reason": "Spread exceeds configured limit",
                "analysis": analysis,
            }

        if signal == "HOLD":
            return {
                "action": "HOLD",
                "reason": "No trading signal",
                "analysis": analysis,
            }

        return {
            "action": signal,
            "reason": "Signal accepted by spread filter",
            "analysis": analysis,
        }

    def execute_paper(
        self,
        engine: PaperTradingEngine,
        order_book: Dict[str, Any],
        base_asset: str,
        quote_asset: str,
        quantity: Any,
        risk_manager: RiskManager,
        signal: str = "HOLD",
    ) -> Dict[str, Any]:
        decision = self.evaluate(order_book, signal)

        if decision["action"] == "HOLD":
            return {
                "decision": decision,
                "executed": False,
                "trade": None,
            }

        qty = to_decimal(quantity)

        if qty <= 0 or qty > self.max_quantity:
            raise ValueError("Quantity exceeds configured limits")

        normalized = normalize_order_book(order_book)

        # Always simulate execution in best-price order.
        asks = sorted(
            normalized["sell"],
            key=lambda level: level["price"],
        )
        bids = sorted(
            normalized["buy"],
            key=lambda level: level["price"],
            reverse=True,
        )

        sorted_book = {
            "sell": [
                [str(level["price"]), str(level["quantity"])]
                for level in asks
            ],
            "buy": [
                [str(level["price"]), str(level["quantity"])]
                for level in bids
            ],
        }

        levels = (
            sorted_book["sell"]
            if decision["action"] == "BUY"
            else sorted_book["buy"]
        )

        # Calculate actual simulated notional across depth.
        remaining = qty
        estimated_notional = Decimal("0")

        for price_str, available_str in levels:
            price = Decimal(price_str)
            available = Decimal(available_str)
            take = min(remaining, available)
            estimated_notional += take * price
            remaining -= take

            if remaining == 0:
                break

        if remaining > 0:
            raise ValueError("Insufficient order book liquidity")

        if estimated_notional > self.max_order_notional:
            raise ValueError("Order exceeds max notional")
        
        allowed, reason = risk_manager.check(estimated_notional)

        if not allowed:
            return {
                "decision": {
                    "action": "HOLD",
                    "reason": reason,
                    "analysis": decision["analysis"],
                },
                "executed": False,
                "trade": None,
            }

        if decision["action"] == "BUY":
            trade = engine.buy_market(
                base_asset, quote_asset, qty, sorted_book
            )
        else:
            trade = engine.sell_market(
                base_asset, quote_asset, qty, sorted_book
            )

        risk_manager.record_trade()

        return {
            "decision": decision,
            "executed": True,
            "trade": trade,
        }
