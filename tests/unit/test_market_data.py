
import pytest

from app.clients.indodax_market_data import IndodaxMarketDataClient


def test_validate_pair_id():
    assert (
        IndodaxMarketDataClient._validate_pair_id("BTCIDR")
        == "btcidr"
    )


def test_reject_invalid_pair_id():
    with pytest.raises(ValueError):
        IndodaxMarketDataClient._validate_pair_id("BTC/IDR")


def test_get_ticker_parses_response(monkeypatch):
    client = IndodaxMarketDataClient()

    def fake_get(path):
        assert path == "/api/ticker/btcidr"
        return {
            "ticker": {
                "last": "100000000",
                "buy": "99900000",
                "sell": "100100000",
            }
        }

    monkeypatch.setattr(client, "_get", fake_get)

    ticker = client.get_ticker("BTCIDR")

    assert ticker["last"] == "100000000"
    assert ticker["buy"] == "99900000"


def test_get_order_book_parses_response(monkeypatch):
    client = IndodaxMarketDataClient()

    def fake_get(path):
        assert path == "/api/depth/btcidr"
        return {
            "buy": [[100000000, "0.01"]],
            "sell": [[100100000, "0.02"]],
        }

    monkeypatch.setattr(client, "_get", fake_get)

    order_book = client.get_order_book("btcidr")

    assert order_book["buy"][0][0] == 100000000
    assert order_book["sell"][0][1] == "0.02"

