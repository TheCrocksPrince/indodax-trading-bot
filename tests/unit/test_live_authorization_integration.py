import pytest

from app.services.telegram_order_journal import (
    TelegramOrderJournal,
)
from app.services.bound_live_authorization_journal import (
    BoundLiveAuthorizationJournal,
)
from app.services.live_authorization_service import (
    LiveAuthorizationService,
)


def setup_service(tmp_path):
    telegram = TelegramOrderJournal(
        tmp_path / "telegram.db"
    )
    authorization = BoundLiveAuthorizationJournal(
        tmp_path / "authorization.db"
    )

    service = LiveAuthorizationService(
        telegram_journal=telegram,
        authorization_journal=authorization,
    )

    return telegram, authorization, service


def create_confirmed_intent(telegram):
    intent_id = telegram.create_intent(
        user_id=12345,
        exchange="binance",
        symbol="BTCUSDT",
        side="BUY",
        quantity="0.0001",
        price="70000",
    )

    telegram.confirm_intent(
        intent_id,
        12345,
    )

    return intent_id


def test_confirmed_intent_can_create_bound_authorization(tmp_path):
    telegram, authorization, service = setup_service(tmp_path)
    intent_id = create_confirmed_intent(telegram)

    result = service.request_authorization(
        intent_id,
        12345,
        "AUTHORIZE LIVE ORDER",
    )

    assert result["status"] == "AUTHORIZED"
    assert result["intent_id"] == intent_id
    assert len(result["fingerprint"]) == 64


def test_authorization_cannot_be_created_twice(tmp_path):
    telegram, authorization, service = setup_service(tmp_path)
    intent_id = create_confirmed_intent(telegram)

    service.request_authorization(
        intent_id, 12345, "AUTHORIZE LIVE ORDER"
    )

    with pytest.raises(PermissionError):
        service.request_authorization(
            intent_id, 12345, "AUTHORIZE LIVE ORDER"
        )


def test_other_user_cannot_authorize(tmp_path):
    telegram, authorization, service = setup_service(tmp_path)
    intent_id = create_confirmed_intent(telegram)

    with pytest.raises(PermissionError):
        service.request_authorization(
            intent_id, 99999, "AUTHORIZE LIVE ORDER"
        )