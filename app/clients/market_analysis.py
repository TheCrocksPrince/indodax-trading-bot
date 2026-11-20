
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List


def to_decimal(value: Any) -> Decimal:
    """Konversi angka ke Decimal tanpa melewati float."""
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Invalid numeric value: {!r}".format(value))

    if not result.is_finite():
        raise ValueError("Value must be finite")

    return result


def normalize_order_book(
    order_book: Dict[str, Any]
) -> Dict[str, List[Dict[str, Decimal]]]:
    """Normalisasi bid/ask menjadi price dan quantity bertipe Decimal."""
    normalized = {}

    for side in ("buy", "sell"):
        levels = order_book.get(side)

        if not isinstance(levels, list):
            raise ValueError("Order book is missing '{}' levels".format(side))

        normalized_levels = []

        for level in levels:
            if not isinstance(level, (list, tuple)) or len(level) != 2:
                raise ValueError("Invalid order book level")

            price = to_decimal(level[0])
            quantity = to_decimal(level[1])

            if price <= 0 or quantity < 0:
                raise ValueError("Price must be positive and quantity non-negative")

            normalized_levels.append({
                "price": price,
                "quantity": quantity,
            })

        normalized[side] = normalized_levels

    return normalized


def analyze_order_book(
    order_book: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Hitung best bid, best ask, spread, dan spread percentage.

    Spread percentage dihitung relatif terhadap best ask:
    (best ask - best bid) / best ask * 100.
    """
    book = normalize_order_book(order_book)

    if not book["buy"] or not book["sell"]:
        raise ValueError("Cannot calculate spread: bid or ask side is empty")

    # Ambil harga terbaik berdasarkan harga, bukan asumsi urutan respons.
    best_bid = max(level["price"] for level in book["buy"])
    best_ask = min(level["price"] for level in book["sell"])

    spread = best_ask - best_bid

    spread_pct = (
        spread / best_ask * Decimal("100")
        if best_ask > 0
        else None
    )

    return {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "spread": spread,
        "spread_pct": spread_pct,
        "book_is_crossed": best_bid > best_ask,
        "book_is_locked": best_bid == best_ask,
    }
