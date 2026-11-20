
from app.clients.paper_trading import PaperTradingEngine
from app.strategies.strategy_engine import SpreadFilterStrategy
from app.strategies.risk_manager import RiskManager


BOOK = {
    "buy": [["99000", "1"]],
    "sell": [["100000", "1"]],
}


def setup_components():
    engine = PaperTradingEngine(
        initial_balances={"IDR": "1000000", "BTC": "1"}
    )
    strategy = SpreadFilterStrategy(
        max_spread_pct="2",
        max_order_notional="100000",
    )
    risk = RiskManager(
        max_position_notional="100000",
        cooldown_seconds=60,
    )
    return engine, strategy, risk


def execute(engine, strategy, risk):
    return strategy.execute_paper(
        engine=engine,
        order_book=BOOK,
        base_asset="BTC",
        quote_asset="IDR",
        quantity="0.1",
        risk_manager=risk,
        signal="BUY",
    )


def test_risk_approved_trade_executes():
    engine, strategy, risk = setup_components()

    result = execute(engine, strategy, risk)

    assert result["executed"] is True
    assert len(engine.trades) == 1


def test_kill_switch_prevents_execution():
    engine, strategy, risk = setup_components()
    risk.stop()

    result = execute(engine, strategy, risk)

    assert result["executed"] is False
    assert result["decision"]["action"] == "HOLD"
    assert len(engine.trades) == 0


def test_cooldown_prevents_second_execution():
    engine, strategy, risk = setup_components()

    first = execute(engine, strategy, risk)
    second = execute(engine, strategy, risk)

    assert first["executed"] is True
    assert second["executed"] is False
    assert "cooldown" in second["decision"]["reason"].lower()
    assert len(engine.trades) == 1


def test_exposure_limit_prevents_execution():
    engine, strategy, risk = setup_components()
    risk.max_position_notional = risk.max_position_notional / 20

    result = execute(engine, strategy, risk)

    assert result["executed"] is False
    assert result["decision"]["action"] == "HOLD"
    assert result["decision"]["reason"] == (
        "Order exceeds max position notional"
    )
    assert len(engine.trades) == 0
