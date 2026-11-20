
from decimal import Decimal
from typing import Any, Dict, List


def dec(value: Any) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("Value must be finite")
    return result


class PaperTradingEngine:
    """
    Simulasi market buy/sell dengan saldo virtual.
    Tidak mengirim request order ke exchange.
    Fee diasumsikan dibebankan dalam quote currency (mis. IDR).
    """

    def __init__(
        self,
        initial_balances: Dict[str, Any],
        fee_rate: Any = "0.001",
    ):
        self.balances = {
            asset.upper(): dec(amount)
            for asset, amount in initial_balances.items()
        }
        self.fee_rate = dec(fee_rate)

        if self.fee_rate < 0:
            raise ValueError("fee_rate cannot be negative")

        if any(amount < 0 for amount in self.balances.values()):
            raise ValueError("Initial balances cannot be negative")

        self.trades: List[Dict[str, Any]] = []

    def _simulate_fill(
        self,
        levels: list,
        quantity: Decimal,
    ):
        """Hitung fill pada level order book tanpa mengubah saldo."""
        remaining = quantity
        notional = Decimal("0")
        fills = []

        for level in levels:
            if not isinstance(level, (list, tuple)) or len(level) != 2:
                raise ValueError("Invalid order book level")

            price = dec(level[0])
            available = dec(level[1])

            if price <= 0 or available < 0:
                raise ValueError("Invalid price or quantity in order book")

            take = min(remaining, available)

            if take > 0:
                notional += take * price
                fills.append({
                    "price": price,
                    "quantity": take,
                })
                remaining -= take

            if remaining == 0:
                break

        if remaining > 0:
            raise ValueError("Insufficient order book liquidity")

        return notional, fills

    def buy_market(
        self,
        base_asset: str,
        quote_asset: str,
        quantity: Any,
        order_book: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Beli sejumlah base asset menggunakan virtual quote balance."""
        base = base_asset.upper()
        quote = quote_asset.upper()
        qty = dec(quantity)

        if qty <= 0:
            raise ValueError("quantity must be positive")

        if "sell" not in order_book:
            raise ValueError("Missing ask side in order book")

        notional, fills = self._simulate_fill(
            order_book["sell"], qty
        )
        fee = notional * self.fee_rate
        total_cost = notional + fee

        if self.balances.get(quote, Decimal("0")) < total_cost:
            raise ValueError("Insufficient virtual quote balance")

        # Saldo hanya berubah setelah semua validasi berhasil.
        self.balances[quote] = (
            self.balances.get(quote, Decimal("0")) - total_cost
        )
        self.balances[base] = (
            self.balances.get(base, Decimal("0")) + qty
        )

        trade = {
            "side": "buy",
            "base_asset": base,
            "quote_asset": quote,
            "quantity": qty,
            "notional": notional,
            "fee": fee,
            "total_cost": total_cost,
            "average_price": notional / qty,
            "fills": fills,
        }
        self.trades.append(trade)
        return trade

    def sell_market(
        self,
        base_asset: str,
        quote_asset: str,
        quantity: Any,
        order_book: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Jual sejumlah base asset menggunakan virtual bid liquidity."""
        base = base_asset.upper()
        quote = quote_asset.upper()
        qty = dec(quantity)

        if qty <= 0:
            raise ValueError("quantity must be positive")

        if self.balances.get(base, Decimal("0")) < qty:
            raise ValueError("Insufficient virtual base balance")

        if "buy" not in order_book:
            raise ValueError("Missing bid side in order book")

        notional, fills = self._simulate_fill(
            order_book["buy"], qty
        )
        fee = notional * self.fee_rate
        net_proceeds = notional - fee

        if net_proceeds < 0:
            raise ValueError("Fee exceeds sale proceeds")

        self.balances[base] -= qty
        self.balances[quote] = (
            self.balances.get(quote, Decimal("0")) + net_proceeds
        )

        trade = {
            "side": "sell",
            "base_asset": base,
            "quote_asset": quote,
            "quantity": qty,
            "notional": notional,
            "fee": fee,
            "net_proceeds": net_proceeds,
            "average_price": notional / qty,
            "fills": fills,
        }
        self.trades.append(trade)
        return trade
