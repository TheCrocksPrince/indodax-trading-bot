import pytest

from scripts.binance_order_journal import (
    BinanceOrderJournal,
    DuplicateOrderIntentError,
    InvalidOrderTransitionError,
)


@pytest.fixture
def journal(tmp_path):
    return BinanceOrderJournal(
        tmp_path / "binance_orders.db"
    )


def create_sample_intent(journal):
    return journal.create_intent(
        intent_id="intent-001",
        client_order_id="bot_001",
        symbol="BTCUSDT",
        side="BUY",
        quantity="0.00012",
        price="50000",
    )


def test_create_intent(journal):
    result = create_sample_intent(journal)

    assert result["status"] == "PENDING"
    assert result["symbol"] == "BTCUSDT"


def test_duplicate_intent_rejected(journal):
    create_sample_intent(journal)

    with pytest.raises(DuplicateOrderIntentError):
        create_sample_intent(journal)


def test_duplicate_client_order_id_rejected(journal):
    create_sample_intent(journal)

    with pytest.raises(DuplicateOrderIntentError):
        journal.create_intent(
            intent_id="intent-002",
            client_order_id="bot_001",
            symbol="BTCUSDT",
            side="BUY",
            quantity="0.00012",
            price="50000",
        )


def test_claim_for_submission(journal):
    create_sample_intent(journal)

    result = journal.claim_for_submission(
        "intent-001"
    )

    assert result["status"] == "SUBMITTING"


def test_double_submission_rejected(journal):
    create_sample_intent(journal)

    journal.claim_for_submission("intent-001")

    with pytest.raises(InvalidOrderTransitionError):
        journal.claim_for_submission("intent-001")


def test_unknown_after_timeout(journal):
    create_sample_intent(journal)
    journal.claim_for_submission("intent-001")

    result = journal.transition(
        "intent-001",
        "SUBMITTING",
        "UNKNOWN",
        error_message="Request timeout",
    )

    assert result["status"] == "UNKNOWN"


def test_reconcile_unknown_order(journal):
    create_sample_intent(journal)
    journal.claim_for_submission("intent-001")

    journal.transition(
        "intent-001",
        "SUBMITTING",
        "UNKNOWN",
    )

    result = journal.transition(
        "intent-001",
        "UNKNOWN",
        "ACKNOWLEDGED",
        exchange_order_id="12345",
    )

    assert result["status"] == "ACKNOWLEDGED"
    assert result["exchange_order_id"] == "12345"


def test_journal_persists_after_restart(tmp_path):
    db_path = tmp_path / "orders.db"

    first = BinanceOrderJournal(db_path)

    create_sample_intent(first)

    second = BinanceOrderJournal(db_path)

    result = second.get_intent("intent-001")

    assert result["status"] == "PENDING"


def test_cannot_revert_to_pending(journal):
    create_sample_intent(journal)
    journal.claim_for_submission("intent-001")

    with pytest.raises(InvalidOrderTransitionError):
        journal.transition(
            "intent-001",
            "SUBMITTING",
            "PENDING",
        )