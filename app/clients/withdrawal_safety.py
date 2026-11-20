
import json
import os
from decimal import Decimal, InvalidOperation
from app.config.settings import settings


def validate_positive_amount(value):
    """
    Validate withdrawal amount without floating-point errors.
    """
    if isinstance(value, bool):
        raise ValueError("Invalid withdrawal amount")

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Invalid withdrawal amount")

    if not amount.is_finite() or amount <= 0:
        raise ValueError("Withdrawal amount must be positive")

    return amount

def _withdraw_config(env_name, settings_name):
    value = os.environ.get(env_name)

    if value is not None:
        return value

    return getattr(settings, settings_name)

def _load_allowlist(env_name):
    """
    Load a withdrawal allowlist from environment variables.
    Fail closed when missing or malformed.
    """
    raw = _withdraw_config(
        env_name,
        env_name.lower(),
    )

    if not raw:
        raise RuntimeError(
            "{} is not configured".format(env_name)
        )

    try:
        entries = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        raise RuntimeError(
            "Invalid JSON in {}".format(env_name)
        )

    if not isinstance(entries, list):
        raise RuntimeError(
            "{} must contain a JSON list".format(env_name)
        )

    return entries


def check_crypto_destination(coin, network, address):
    """
    Only permit a crypto destination explicitly allowlisted
    for the exact asset and network.
    """
    entries = _load_allowlist(
        "INDODAX_WITHDRAW_ALLOWLIST"
    )

    allowed = any(
        isinstance(item, dict)
        and item.get("coin") == coin
        and item.get("network") == network
        and item.get("address") == address
        for item in entries
    )

    if not allowed:
        raise PermissionError(
            "Crypto withdrawal destination is not allowlisted"
        )

    return True


def check_idr_destination(account_number, bank_code):
    """
    Only permit an explicitly approved bank account.
    Keep account numbers as strings to preserve leading zeros.
    """
    entries = _load_allowlist(
        "INDODAX_IDR_WITHDRAW_ALLOWLIST"
    )

    allowed = any(
        isinstance(item, dict)
        and item.get("accountNumber") == account_number
        and item.get("bankCodeForPix") == bank_code
        for item in entries
    )

    if not allowed:
        raise PermissionError(
            "IDR withdrawal destination is not allowlisted"
        )

    return True


def check_live_withdrawal_enabled():
    env_value = os.environ.get(
        "INDODAX_ENABLE_LIVE_WITHDRAWAL"
    )

    if env_value is not None:
        enabled = env_value == "true"
    else:
        enabled = settings.indodax_enable_live_withdrawal is True

    if not enabled:
        raise RuntimeError(
            "Live withdrawal is disabled. "
            "Set INDODAX_ENABLE_LIVE_WITHDRAWAL=true "
            "only after completing all safety checks."
        )

    return True
