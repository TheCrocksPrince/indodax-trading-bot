from concurrent.futures import ThreadPoolExecutor

import pytest

from app.services.execution_claim_journal import (
    ExecutionClaimJournal,
)


def test_claim_only_once(tmp_path):
    journal = ExecutionClaimJournal(
        tmp_path / "claims.db"
    )

    journal.claim("intent-001", "fingerprint-001")

    with pytest.raises(PermissionError):
        journal.claim(
            "intent-001",
            "fingerprint-001",
        )


def test_concurrent_claim_only_one_wins(tmp_path):
    journal = ExecutionClaimJournal(
        tmp_path / "claims.db"
    )

    def attempt(_):
        try:
            journal.claim(
                "intent-concurrent",
                "fingerprint-001",
            )
            return True
        except PermissionError:
            return False

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(attempt, range(20)))

    assert results.count(True) == 1
    assert results.count(False) == 19


def test_claim_persists_across_instances(tmp_path):
    db_path = tmp_path / "claims.db"

    first = ExecutionClaimJournal(db_path)
    first.claim(
        "intent-persistent",
        "fingerprint-001",
    )

    second = ExecutionClaimJournal(db_path)

    with pytest.raises(PermissionError):
        second.claim(
            "intent-persistent",
            "fingerprint-001",
        )