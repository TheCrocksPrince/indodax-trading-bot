import pytest

from app.services.order_fingerprint import order_fingerprint


BASE = {
    "intent_id": "intent-001",
    "user_id": 12345,
    "exchange": "binance",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "quantity": "0.0001",
    "price": "70000",
}


def test_same_order_same_fingerprint():
    first = order_fingerprint(**BASE)

    second = order_fingerprint(
        **{
            **BASE,
            "quantity": "0.000100",
            "price": "70000.00",
        }
    )

    assert first == second


@pytest.mark.parametrize(
    "field,new_value",
    [
        ("user_id", 99999),
        ("exchange", "indodax"),
        ("symbol", "ETHUSDT"),
        ("side", "SELL"),
        ("quantity", "0.0002"),
        ("price", "71000"),
        ("intent_id", "intent-002"),
    ],
)
def test_changed_order_changes_fingerprint(
    field,
    new_value,
):
    modified = {
        **BASE,
        field: new_value,
    }

    assert order_fingerprint(
        **BASE
    ) != order_fingerprint(
        **modified
    )


def test_rejects_invalid_quantity():
    with pytest.raises(ValueError):
        order_fingerprint(
            **{
                **BASE,
                "quantity": "-1",
            }
        )


def test_rejects_cancel_without_order_schema():
    with pytest.raises(ValueError):
        order_fingerprint(
            **BASE,
            action="CANCEL",
        )