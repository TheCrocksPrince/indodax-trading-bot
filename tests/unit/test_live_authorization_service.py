import pytest

from app.services.live_authorization_service import (
    LiveAuthorizationService,
)
from app.services.live_authorization_journal import (
    LiveAuthorizationJournal,
)
from app.services.telegram_order_journal import (
    TelegramOrderJournal,
)


def test_rejects_incorrect_confirmation(tmp_path):
    service = LiveAuthorizationService(
        telegram_journal=TelegramOrderJournal(
            tmp_path / "telegram.db"
        ),
        authorization_journal=LiveAuthorizationJournal(
            tmp_path / "authorization.db"
        ),
    )

    with pytest.raises(PermissionError):
        service.request_authorization(
            intent_id="intent-001",
            user_id=12345,
            confirmation="CONFIRM",
        )


def test_rejects_missing_intent(tmp_path):
    service = LiveAuthorizationService(
        telegram_journal=TelegramOrderJournal(
            tmp_path / "telegram.db"
        ),
        authorization_journal=LiveAuthorizationJournal(
            tmp_path / "authorization.db"
        ),
    )

    with pytest.raises(PermissionError):
        service.request_authorization(
            intent_id="missing",
            user_id=12345,
            confirmation="AUTHORIZE LIVE ORDER",
        )