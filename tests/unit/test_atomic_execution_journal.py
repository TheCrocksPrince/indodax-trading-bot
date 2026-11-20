from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from app.services.atomic_execution_journal import (
    AtomicExecutionJournal,
)


def setup_journal(tmp_path):
    journal = AtomicExecutionJournal(tmp_path / "atomic.db")

    expiry = (
        datetime.now(timezone.utc) + timedelta(minutes=1)
    ).isoformat()

    journal.register_authorization(
        "intent-001",
        12345,
        "binance",
        "fingerprint-001",
        expiry,
    )

    return journal


def claim(journal, fingerprint="fingerprint-001"):
    return journal.claim_authorized(
        "intent-001",
        12345,
        "binance",
        fingerprint,
    )


def test_authorization_and_claim_succeed(tmp_path):
    journal = setup_journal(tmp_path)

    result = claim(journal)

    assert result["status"] == "CLAIMED"


def test_cannot_claim_twice(tmp_path):
    journal = setup_journal(tmp_path)

    claim(journal)

    with pytest.raises(PermissionError):
        claim(journal)


def test_wrong_fingerprint_does_not_consume(tmp_path):
    journal = setup_journal(tmp_path)

    with pytest.raises(PermissionError):
        claim(journal, "wrong-fingerprint")

    assert claim(journal)["status"] == "CLAIMED"


def test_concurrent_claim_only_one_succeeds(tmp_path):
    journal = setup_journal(tmp_path)

    def attempt(_):
        try:
            claim(journal)
            return True
        except PermissionError:
            return False

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(attempt, range(20)))

    assert results.count(True) == 1
    assert results.count(False) == 19


def test_expired_authorization_rejected(tmp_path):
    journal = AtomicExecutionJournal(tmp_path / "atomic.db")

    expired = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
    ).isoformat()

    with pytest.raises(PermissionError):
        journal.register_authorization(
            "intent-001",
            12345,
            "binance",
            "fingerprint-001",
            expired,
        )


def test_claim_persists_after_restart(tmp_path):
    journal = setup_journal(tmp_path)
    claim(journal)

    restarted = AtomicExecutionJournal(
        tmp_path / "atomic.db"
    )

    with pytest.raises(PermissionError):
        claim(restarted)