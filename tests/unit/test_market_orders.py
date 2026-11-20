
import pytest

from app.clients.indodax_client import IndodaxClient
from unittest.mock import Mock, patch


@pytest.fixture
def client():
    return IndodaxClient(
        api_key="test-key",
        secret_key="test-secret",
        base_url="https://example.test",
    )


def test_market_buy_dry_run(client):
    result = client.create_order(
        symbol="BTCIDR",
        side="BUY",
        order_type="MARKET",
        quote_order_qty=100000,
    )

    params = result["params"]

    assert params["type"] == "MARKET"
    assert params["side"] == "BUY"
    assert params["quoteOrderQty"] == "100000"
    assert "price" not in params
    assert "quantity" not in params
    assert "timeInForce" not in params
    assert result["sent"] is False


def test_market_sell_dry_run(client):
    result = client.create_order(
        symbol="BTCIDR",
        side="SELL",
        order_type="MARKET",
        quantity="0.001",
    )

    params = result["params"]

    assert params["type"] == "MARKET"
    assert params["side"] == "SELL"
    assert params["quantity"] == "0.001"
    assert "price" not in params
    assert "quoteOrderQty" not in params
    assert "timeInForce" not in params
    assert result["sent"] is False


def test_limit_buy_backward_compatible(client):
    result = client.create_order(
        symbol="BTCIDR",
        side="BUY",
        price="1000000000",
        quantity="0.001",
        time_in_force="GTC",
    )

    assert result["params"]["type"] == "LIMIT"
    assert result["params"]["timeInForce"] == "GTC"


def test_limit_moc_preserved(client):
    result = client.create_order(
        symbol="BTCIDR",
        side="SELL",
        price="1000000000",
        quantity="0.001",
        time_in_force="MOC",
    )

    assert result["params"]["timeInForce"] == "MOC"


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": "0.001",
        },
        {
            "side": "BUY",
            "order_type": "MARKET",
            "quote_order_qty": "100.5",
        },
        {
            "side": "SELL",
            "order_type": "MARKET",
            "quote_order_qty": 100000,
        },
        {
            "side": "SELL",
            "order_type": "MARKET",
            "quantity": "-1",
        },
        {
            "side": "BUY",
            "order_type": "LIMIT",
            "price": "1000",
        },
    ],
)
def test_invalid_order_parameters(client, kwargs):
    with pytest.raises(ValueError):
        client.create_order(symbol="BTCIDR", **kwargs)

def test_market_order_live_submission(client):
    mock_response = Mock()
    mock_response.json.return_value = {
        "orderId": 12345,
        "status": "NEW"
    }
    mock_response.raise_for_status.return_value = None

    with patch(
        "app.clients.indodax_client.httpx.post",
        return_value=mock_response
    ) as mock_post:

        result = client.create_order(
            symbol="BTCIDR",
            side="BUY",
            order_type="MARKET",
            quote_order_qty=100000,
            dry_run=False
        )

    mock_post.assert_called_once()

    assert result["orderId"] == 12345
    assert result["status"] == "NEW"


def test_limit_order_live_submission(client):
    mock_response = Mock()
    mock_response.json.return_value = {
        "orderId": 12346,
        "status": "NEW"
    }
    mock_response.raise_for_status.return_value = None

    with patch(
        "app.clients.indodax_client.httpx.post",
        return_value=mock_response
    ) as mock_post:

        result = client.create_order(
            symbol="BTCIDR",
            side="BUY",
            order_type="LIMIT",
            price="1000000000",
            quantity="0.001",
            dry_run=False
        )

    mock_post.assert_called_once()

    assert result["orderId"] == 12346



