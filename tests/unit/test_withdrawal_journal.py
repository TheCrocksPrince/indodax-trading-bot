
import pytest

from app.clients.withdrawal_journal import (
    DuplicateWithdrawalError,
    WithdrawalJournal,
)


@pytest.fixture
def journal(tmp_path):
    return WithdrawalJournal(
        db_path=str(tmp_path / "withdrawals.db")
    )


@pytest.fixture
def payload():
    return {
        "coin": "BTC",
        "network": "BTC",
        "address": "test-address",
        "amount": "0.001",
    }


def test_reserve_request(journal, payload):
    result = journal.reserve(
        "CRYPTO", "request001", payload
    )

    assert result["status"] == "RESERVED"
    assert result["request_id"] == "request001"
    assert len(result["payload_hash"]) == 64


def test_duplicate_request_rejected(journal, payload):
    journal.reserve("CRYPTO", "request001", payload)

    with pytest.raises(DuplicateWithdrawalError):
        journal.reserve("CRYPTO", "request001", payload)


def test_duplicate_rejected_with_different_payload(
    journal, payload
):
    journal.reserve("CRYPTO", "request001", payload)

    changed = dict(payload)
    changed["amount"] = "0.002"

    with pytest.raises(DuplicateWithdrawalError):
        journal.reserve("CRYPTO", "request001", changed)


def test_submitting_transition(journal, payload):
    journal.reserve("CRYPTO", "request001", payload)

    result = journal.mark_submitting(
        "CRYPTO", "request001"
    )

    assert result["status"] == "SUBMITTING"


def test_submitting_cannot_repeat(journal, payload):
    journal.reserve("CRYPTO", "request001", payload)
    journal.mark_submitting("CRYPTO", "request001")

    with pytest.raises(RuntimeError):
        journal.mark_submitting("CRYPTO", "request001")


def test_success_result(journal, payload):
    journal.reserve("CRYPTO", "request001", payload)
    journal.mark_submitting("CRYPTO", "request001")

    result = journal.mark_result(
        "CRYPTO",
        "request001",
        "SUCCESS",
        {"id": "withdraw123"},
    )

    assert result["status"] == "SUCCESS"
    assert result["response"]["id"] == "withdraw123"


def test_unknown_result(journal, payload):
    journal.reserve("CRYPTO", "request001", payload)
    journal.mark_submitting("CRYPTO", "request001")

    result = journal.mark_result(
        "CRYPTO", "request001", "UNKNOWN"
    )

    assert result["status"] == "UNKNOWN"


def test_unknown_cannot_be_resubmitted(
    journal, payload
):
    journal.reserve("CRYPTO", "request001", payload)
    journal.mark_submitting("CRYPTO", "request001")
    journal.mark_result(
        "CRYPTO", "request001", "UNKNOWN"
    )

    with pytest.raises(RuntimeError):
        journal.mark_submitting("CRYPTO", "request001")


def test_persistence_across_instances(tmp_path, payload):
    db_path = str(tmp_path / "withdrawals.db")

    first = WithdrawalJournal(db_path)
    first.reserve("CRYPTO", "request001", payload)

    second = WithdrawalJournal(db_path)

    assert second.get(
        "CRYPTO", "request001"
    )["status"] == "RESERVED"


def test_list_requests(journal, payload):
    journal.reserve("CRYPTO", "request001", payload)
    journal.reserve("IDR", "request002", {"amount": 200000})

    results = journal.list_requests()

    assert len(results) == 2
    assert results[0]["request_id"] == "request002"


def test_invalid_type_rejected(journal, payload):
    with pytest.raises(ValueError):
        journal.reserve("OTHER", "request001", payload)


def test_result_requires_submitting(journal, payload):
    journal.reserve("CRYPTO", "request001", payload)

    with pytest.raises(RuntimeError):
        journal.mark_result(
            "CRYPTO", "request001", "SUCCESS"
        )
