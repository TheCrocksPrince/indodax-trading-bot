
from decimal import Decimal
from typing import Any, Dict

from app.clients.market_analysis import (
    normalize_order_book,
    to_decimal,
)


class OrderBookSignal:
    """
    Menghasilkan sinyal berdasarkan order book imbalance.

    Ini strategi eksperimen, bukan prediksi harga yang tervalidasi.
    """

    def __init__(
        self,
        depth: int = 5,
        buy_threshold: Any = "0.3",
        sell_threshold: Any = "-0.3",
    ):
        if isinstance(depth, bool) or not isinstance(depth, int) or depth <= 0:
            raise ValueError("depth must be a positive integer")

        self.depth = depth
        self.buy_threshold = to_decimal(buy_threshold)
        self.sell_threshold = to_decimal(sell_threshold)

        if not (
            Decimal("-1") <= self.sell_threshold
            < Decimal("0")
            < self.buy_threshold <= Decimal("1")
        ):
            raise ValueError("Invalid signal thresholds")

    def generate(self, order_book: Dict[str, Any]) -> Dict[str, Any]:
        book = normalize_order_book(order_book)

        # Remove zero-quantity levels and sort by best price.
        bids = sorted(
            [level for level in book["buy"] if level["quantity"] > 0],
            key=lambda level: level["price"],
            reverse=True,
        )[:self.depth]

        asks = sorted(
            [level for level in book["sell"] if level["quantity"] > 0],
            key=lambda level: level["price"],
        )[:self.depth]

        if not bids or not asks:
            return {
                "signal": "HOLD",
                "imbalance": Decimal("0"),
                "reason": "Insufficient order book depth",
            }

        if bids[0]["price"] >= asks[0]["price"]:
            return {
                "signal": "HOLD",
                "imbalance": Decimal("0"),
                "reason": "Crossed or locked order book",
            }

        bid_volume = sum(
            (level["quantity"] for level in bids),
            Decimal("0"),
        )
        ask_volume = sum(
            (level["quantity"] for level in asks),
            Decimal("0"),
        )

        total_volume = bid_volume + ask_volume

        if total_volume == 0:
            return {
                "signal": "HOLD",
                "imbalance": Decimal("0"),
                "reason": "No available liquidity",
            }

        imbalance = (bid_volume - ask_volume) / total_volume

        if imbalance >= self.buy_threshold:
            signal = "BUY"
        elif imbalance <= self.sell_threshold:
            signal = "SELL"
        else:
            signal = "HOLD"

        return {
            "signal": signal,
            "imbalance": imbalance,
            "bid_volume": bid_volume,
            "ask_volume": ask_volume,
            "reason": "Order book imbalance evaluated",
        }
