
import httpx
import pytest
from unittest.mock import MagicMock, patch

from app.clients.indodax_client import IndodaxClient
from app.clients.withdrawal_journal import (
    DuplicateWithdrawalError,
    WithdrawalJournal,
)


@pytest.fixture
def client():
    client = object.__new__(IndodaxClient)
    client.base_url = "https://example.test"
    client.signer = MagicMock()
    client.signer.sign.return_value = "signature"
    client._build_headers = MagicMock(
        return_value={"X-APIKEY": "test-key"}
    )
    return client


@pytest.fixture
def journal_patch(tmp_path):
    db_path = str(tmp_path / "withdrawals.db")

    def factory():
        return WithdrawalJournal(db_path)

    with patch(
        "app.clients.indodax_client.WithdrawalJournal",
        side_effect=factory,
    ):
        yield factory


def submit(client, request_id, validator):
    return client._submit_withdrawal_once(
        withdrawal_type="CRYPTO",
        request_id=request_id,
        payload={
            "coin": "BTC",
            "amount": "0.001",
        },
        endpoint="/api/v2/capital/withdraw/apply",
        signed_params={
            "coin": "BTC",
            "timestamp": 123456,
        },
        success_validator=validator,
    )


def test_success_recorded(client, journal_patch):
    response = MagicMock()
    response.json.return_value = {
        "id": "123",
        "withdrawOrderId": "req001",
    }

    with patch(
        "app.clients.indodax_client.httpx.post",
        return_value=response,
    ) as post:
        result = submit(
            client,
            "req001",
            lambda r: r.get("withdrawOrderId") == "req001",
        )

    assert result["id"] == "123"
    assert post.call_count == 1

    record = journal_patch().get("CRYPTO", "req001")
    assert record["status"] == "SUCCESS"


def test_duplicate_never_sends_twice(
    client, journal_patch
):
    response = MagicMock()
    response.json.return_value = {"id": "123"}

    with patch(
        "app.clients.indodax_client.httpx.post",
        return_value=response,
    ) as post:
        submit(client, "req002", lambda r: True)

        with pytest.raises(DuplicateWithdrawalError):
            submit(client, "req002", lambda r: True)

    assert post.call_count == 1


def test_timeout_recorded_unknown(
    client, journal_patch
):
    with patch(
        "app.clients.indodax_client.httpx.post",
        side_effect=httpx.ReadTimeout("Timed out"),
    ) as post:
        with pytest.raises(httpx.ReadTimeout):
            submit(client, "req003", lambda r: True)

    assert post.call_count == 1

    record = journal_patch().get("CRYPTO", "req003")
    assert record["status"] == "UNKNOWN"


def test_ambiguous_response_recorded_unknown(
    client, journal_patch
):
    response = MagicMock()
    response.json.return_value = {
        "unexpected": "response"
    }

    with patch(
        "app.clients.indodax_client.httpx.post",
        return_value=response,
    ):
        with pytest.raises(RuntimeError):
            submit(
                client,
                "req004",
                lambda r: "id" in r,
            )

    record = journal_patch().get("CRYPTO", "req004")
    assert record["status"] == "UNKNOWN"


def test_timeout_cannot_be_retried(
    client, journal_patch
):
    with patch(
        "app.clients.indodax_client.httpx.post",
        side_effect=httpx.ReadTimeout("Timed out"),
    ) as post:
        with pytest.raises(httpx.ReadTimeout):
            submit(client, "req005", lambda r: True)

        with pytest.raises(DuplicateWithdrawalError):
            submit(client, "req005", lambda r: True)

    assert post.call_count == 1


def test_http_error_recorded_unknown(
    client, journal_patch
):
    response = MagicMock()
    response.raise_for_status.side_effect = (
        httpx.HTTPStatusError(
            "HTTP error",
            request=httpx.Request(
                "POST", "https://example.test"
            ),
            response=httpx.Response(400),
        )
    )

    with patch(
        "app.clients.indodax_client.httpx.post",
        return_value=response,
    ):
        with pytest.raises(httpx.HTTPStatusError):
            submit(client, "req006", lambda r: True)

    assert journal_patch().get(
        "CRYPTO", "req006"
    )["status"] == "UNKNOWN"
