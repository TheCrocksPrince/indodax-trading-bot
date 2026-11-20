
from decimal import Decimal

from app.clients.paper_trade_store import PaperTradeStore


def test_save_and_read_paper_trade(tmp_path):
    db_path = tmp_path / "paper_trades.db"
    store = PaperTradeStore(str(db_path))

    trade = {
        "side": "buy",
        "base_asset": "BTC",
        "quote_asset": "IDR",
        "quantity": Decimal("0.01"),
        "notional": Decimal("1000000"),
        "fee": Decimal("1000"),
        "total_cost": Decimal("1001000"),
        "average_price": Decimal("100000000"),
        "fills": [
            {
                "price": Decimal("100000000"),
                "quantity": Decimal("0.01"),
            }
        ],
    }

    trade_id = store.save_trade(trade)
    rows = store.list_trades()

    assert trade_id == 1
    assert len(rows) == 1
    assert rows[0]["symbol"] == "BTCIDR"
    assert rows[0]["side"] == "BUY"
    assert rows[0]["quantity"] == "0.01"
    assert rows[0]["details"]["fills"][0]["price"] == "100000000"


def test_trade_history_persists_between_store_instances(tmp_path):
    db_path = tmp_path / "paper_trades.db"
    first_store = PaperTradeStore(str(db_path))

    first_store.save_trade({
        "side": "sell",
        "base_asset": "BTC",
        "quote_asset": "IDR",
        "quantity": Decimal("0.01"),
        "notional": Decimal("900000"),
        "fee": Decimal("900"),
        "net_proceeds": Decimal("899100"),
        "average_price": Decimal("90000000"),
        "fills": [],
    })

    second_store = PaperTradeStore(str(db_path))
    rows = second_store.list_trades()

    assert len(rows) == 1
    assert rows[0]["side"] == "SELL"


def test_list_trades_rejects_invalid_limit(tmp_path):
    store = PaperTradeStore(str(tmp_path / "paper_trades.db"))

    try:
        store.list_trades(limit=0)
        assert False, "Expected ValueError"
    except ValueError:
        pass
