import pytest

from app.services.binance_execution_guard import (
    BinanceExecutionGuard,
)


def test_live_trading_disabled(monkeypatch):
    monkeypatch.setenv(
        "BINANCE_ENABLE_LIVE_TRADING", "false"
    )

    guard = BinanceExecutionGuard()

    with pytest.raises(PermissionError):
        guard.require_live_enabled()


def test_order_exceeds_limit(monkeypatch):
    monkeypatch.setenv(
        "BINANCE_ENABLE_LIVE_TRADING", "true"
    )
    monkeypatch.setenv(
        "BINANCE_MAX_ORDER_NOTIONAL_USDT", "10"
    )

    guard = BinanceExecutionGuard()

    with pytest.raises(PermissionError):
        guard.validate(
            "BTCUSDT", "BUY", "0.01", "50000"
        )


def test_valid_order_parameters(monkeypatch):
    monkeypatch.setenv(
        "BINANCE_ENABLE_LIVE_TRADING", "true"
    )
    monkeypatch.setenv(
        "BINANCE_MAX_ORDER_NOTIONAL_USDT", "10"
    )

    guard = BinanceExecutionGuard()

    result = guard.validate(
        "BTCUSDT", "BUY", "0.00001", "50000"
    )

    assert result["notional_usdt"] == "0.50000"