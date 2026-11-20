
import pytest

from app.clients.withdrawal_safety import (
    validate_positive_amount,
    check_crypto_destination,
    check_idr_destination,
    check_live_withdrawal_enabled,
)


def test_valid_withdrawal_amount():
    assert str(validate_positive_amount("0.001")) == "0.001"


@pytest.mark.parametrize(
    "value",
    ["0", "-1", "abc", "NaN", "Infinity", True],
)
def test_invalid_withdrawal_amount(value):
    with pytest.raises(ValueError):
        validate_positive_amount(value)


def test_crypto_destination_allowlisted(monkeypatch):
    monkeypatch.setenv(
        "INDODAX_WITHDRAW_ALLOWLIST",
        '[{"coin":"BTC","network":"BTC","address":"test-address"}]',
    )

    assert check_crypto_destination(
        "BTC", "BTC", "test-address"
    )


def test_crypto_destination_rejected(monkeypatch):
    monkeypatch.setenv(
        "INDODAX_WITHDRAW_ALLOWLIST",
        "[]",
    )

    with pytest.raises(PermissionError):
        check_crypto_destination(
            "BTC", "BTC", "unknown-address"
        )


def test_idr_destination_allowlisted(monkeypatch):
    monkeypatch.setenv(
        "INDODAX_IDR_WITHDRAW_ALLOWLIST",
        '[{"accountNumber":"0012345678","bankCodeForPix":"014"}]',
    )

    assert check_idr_destination(
        "0012345678", "014"
    )


def test_idr_destination_rejected(monkeypatch):
    monkeypatch.setenv(
        "INDODAX_IDR_WITHDRAW_ALLOWLIST",
        "[]",
    )

    with pytest.raises(PermissionError):
        check_idr_destination(
            "0012345678", "014"
        )


def test_live_withdrawal_disabled_by_default(monkeypatch):
    monkeypatch.setenv(
        "INDODAX_ENABLE_LIVE_WITHDRAWAL",
        "false",
    )

    with pytest.raises(RuntimeError):
        check_live_withdrawal_enabled()


def test_live_withdrawal_explicitly_enabled(monkeypatch):
    monkeypatch.setenv(
        "INDODAX_ENABLE_LIVE_WITHDRAWAL",
        "true",
    )

    assert check_live_withdrawal_enabled()

from unittest.mock import patch

def test_live_withdrawal_uses_settings_when_env_missing(monkeypatch):
    monkeypatch.delenv(
        "INDODAX_ENABLE_LIVE_WITHDRAWAL",
        raising=False,
    )

    with patch(
        "app.clients.withdrawal_safety.settings"
    ) as mock_settings:
        mock_settings.indodax_enable_live_withdrawal = True

        assert check_live_withdrawal_enabled() is True
