
from datetime import datetime, timedelta, timezone

from app.strategies.risk_manager import RiskManager


def test_order_within_limits_is_allowed():
    risk = RiskManager(cooldown_seconds=60)

    allowed, reason = risk.check("15000")

    assert allowed is True
    assert reason == "Risk checks passed"


def test_order_exceeding_limit_is_blocked():
    risk = RiskManager(max_position_notional="10000")

    allowed, reason = risk.check("15000")

    assert allowed is False
    assert reason == "Order exceeds max position notional"


def test_kill_switch_blocks_order():
    risk = RiskManager()
    risk.stop()

    allowed, reason = risk.check("1000")

    assert allowed is False
    assert reason == "Kill switch is active"


def test_cooldown_blocks_repeated_trade():
    risk = RiskManager(cooldown_seconds=60)
    now = datetime(2026, 10, 22, tzinfo=timezone.utc)

    risk.record_trade(now=now)

    allowed, reason = risk.check(
        "1000",
        now=now + timedelta(seconds=30),
    )

    assert allowed is False
    assert reason == "Trading cooldown active"


def test_daily_loss_limit_blocks_order():
    risk = RiskManager(max_daily_loss="5000")
    now = datetime(2026, 10, 22, tzinfo=timezone.utc)

    risk.record_trade(realized_pnl="-5000", now=now)

    allowed, reason = risk.check(
        "1000",
        now=now + timedelta(seconds=120),
    )

    assert allowed is False
    assert reason == "Daily loss limit reached"


def test_negative_notional_is_rejected():
    risk = RiskManager()

    allowed, reason = risk.check("-100")

    assert allowed is False
    assert reason == "Invalid order notional"
