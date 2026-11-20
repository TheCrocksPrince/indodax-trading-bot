
import hashlib
import hmac
from urllib.parse import parse_qs, urlencode

import httpx
import pytest

from app.clients.indodax_client import IndodaxClient
from unittest.mock import Mock, patch


@pytest.fixture
def client():
    return IndodaxClient(
        api_key="test-api-key",
        secret_key="test-secret",
        base_url="https://example.test",
    )


def expected_signature(params):
    encoded = urlencode(params)
    return hmac.new(
        b"test-secret",
        encoded.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()



def test_create_order_prepares_signed_form_body(client, monkeypatch):
    from urllib.parse import urlencode

    def forbidden_post(*args, **kwargs):
        raise AssertionError("HTTP POST must not be called")

    monkeypatch.setattr(
        "app.clients.indodax_client.httpx.post",
        forbidden_post,
    )

    result = client.create_order(
        symbol="BTCIDR",
        side="BUY",
        price="1000000000",
        quantity="0.00001",
        dry_run=True,
    )

    params = result["params"]

    assert result["mode"] == "DRY_RUN"
    assert result["method"] == "POST"
    assert result["endpoint"] == "/api/v2/order"
    assert result["signed"] is True
    assert result["sent"] is False

    assert params["symbol"] == "BTCIDR"
    assert params["side"] == "BUY"
    assert params["type"] == "LIMIT"
    assert params["price"] == "1000000000"
    assert params["quantity"] == "0.00001"
    assert params["timeInForce"] == "GTC"

    assert "timestamp" in params
    assert "recvWindow" in params

    # Verify the signed payload can be form-encoded.
    body = urlencode(params)
    assert "symbol=BTCIDR" in body
    assert "side=BUY" in body


def test_cancel_order_prepares_signed_query(client, monkeypatch):
    def fail_if_delete_called(*args, **kwargs):
        raise AssertionError(
            "HTTP DELETE must not be called during dry-run"
        )

    monkeypatch.setattr(
        "app.clients.indodax_client.httpx.delete",
        fail_if_delete_called,
    )

    result = client.cancel_order(
        symbol="BTCIDR",
        order_id=6423,
        dry_run=True,
    )

    assert result["mode"] == "DRY_RUN"
    assert result["method"] == "DELETE"
    assert result["endpoint"] == "/api/v2/order"
    assert result["sent"] is False
    assert result["signed"] is True

    params = result["params"]

    assert params["symbol"] == "BTCIDR"
    assert params["orderId"] == 6423
    assert "timestamp" in params
    assert "recvWindow" in params


def test_dry_run_never_sends_request(client, monkeypatch):
    def forbidden_request(*args, **kwargs):
        raise AssertionError("HTTP request must not be sent")

    monkeypatch.setattr(
        "app.clients.indodax_client.httpx.post",
        forbidden_request,
    )
    monkeypatch.setattr(
        "app.clients.indodax_client.httpx.delete",
        forbidden_request,
    )

    create_result = client.create_order(
        "BTCIDR", "BUY", "1000000000", "0.00001"
    )
    cancel_result = client.cancel_order("BTCIDR", 6423)

    assert create_result["sent"] is False
    assert cancel_result["sent"] is False

def test_cancel_order_live_submission(client):
    mock_response = Mock()
    mock_response.json.return_value = {
        "orderId": 6423,
        "status": "CANCELED"
    }
    mock_response.raise_for_status.return_value = None

    with patch(
        "app.clients.indodax_client.httpx.delete",
        return_value=mock_response
    ) as mock_delete:

        result = client.cancel_order(
            symbol="BTCIDR",
            order_id=6423,
            dry_run=False
        )

    mock_delete.assert_called_once()

    assert result["orderId"] == 6423
    assert result["status"] == "CANCELED"