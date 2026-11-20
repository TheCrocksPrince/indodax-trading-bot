
from datetime import datetime, timezone
from decimal import Decimal

from app.clients.market_analysis import to_decimal


class RiskManager:
    """Risk controls for a single in-memory paper trading session."""

    def __init__(
        self,
        max_position_notional="100000",
        max_daily_loss="50000",
        cooldown_seconds=60,
        enabled=True,
    ):
        self.max_position_notional = to_decimal(max_position_notional)
        self.max_daily_loss = to_decimal(max_daily_loss)
        self.cooldown_seconds = cooldown_seconds
        self.enabled = enabled
        self.last_trade_at = None
        self.daily_pnl = Decimal("0")
        self.current_day = datetime.now(timezone.utc).date()

        if self.max_position_notional <= 0:
            raise ValueError("max_position_notional must be positive")
        if self.max_daily_loss <= 0:
            raise ValueError("max_daily_loss must be positive")
        if (
            isinstance(cooldown_seconds, bool)
            or not isinstance(cooldown_seconds, (int, float))
            or cooldown_seconds < 0
        ):
            raise ValueError("Invalid cooldown")

    def check(self, proposed_notional, now=None):
        now = now or datetime.now(timezone.utc)

        if not self.enabled:
            return False, "Kill switch is active"

        notional = to_decimal(proposed_notional)

        if notional <= 0:
            return False, "Invalid order notional"

        if notional > self.max_position_notional:
            return False, "Order exceeds max position notional"

        if now.date() != self.current_day:
            self.current_day = now.date()
            self.daily_pnl = Decimal("0")

        if self.daily_pnl <= -self.max_daily_loss:
            return False, "Daily loss limit reached"

        if self.last_trade_at is not None:
            elapsed = (now - self.last_trade_at).total_seconds()

            if elapsed < self.cooldown_seconds:
                return False, "Trading cooldown active"

        return True, "Risk checks passed"

    def record_trade(self, realized_pnl="0", now=None):
        now = now or datetime.now(timezone.utc)

        if now.date() != self.current_day:
            self.current_day = now.date()
            self.daily_pnl = Decimal("0")

        self.daily_pnl += to_decimal(realized_pnl)
        self.last_trade_at = now

    def stop(self):
        self.enabled = False

    def start(self):
        self.enabled = True
