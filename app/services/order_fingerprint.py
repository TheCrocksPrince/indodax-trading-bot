import hashlib
import json
from decimal import Decimal, InvalidOperation


def normalize_decimal(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Invalid decimal value")

    if not number.is_finite() or number <= 0:
        raise ValueError("Order values must be positive and finite")

    return format(number.normalize(), "f")


def order_fingerprint(
    intent_id,
    user_id,
    exchange,
    symbol,
    side,
    quantity,
    price,
    action="CREATE",
):
    if action not in ("CREATE", "CANCEL"):
        raise ValueError("Unsupported action")

    if action != "CREATE":
        raise ValueError(
            "CANCEL requires a separate order-specific schema"
        )

    payload = {
        "intent_id": str(intent_id),
        "user_id": int(user_id),
        "exchange": str(exchange).lower(),
        "symbol": str(symbol).upper(),
        "side": str(side).upper(),
        "quantity": normalize_decimal(quantity),
        "price": normalize_decimal(price),
        "action": action,
    }

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()