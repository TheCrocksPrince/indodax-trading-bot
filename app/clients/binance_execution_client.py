from uuid import uuid4

from app.clients.binance_client import BinanceClient
from app.clients.binance_execution_transport import (
    BinanceExecutionTransport,
)
from app.services.binance_execution_guard import (
    BinanceExecutionGuard,
)
from app.services.binance_order_filters import (
    validate_limit_order_filters,
)
from uuid import uuid4

from scripts.binance_order_journal import (
    BinanceOrderJournal,
)


class BinanceExecutionClient:
    def __init__(self, client=None, guard=None, transport=None, journal=None):
        self.client = client or BinanceClient()
        self.guard = guard or BinanceExecutionGuard()
        self.transport = transport or BinanceExecutionTransport(
            client=self.client
        )
        self.journal = journal or BinanceOrderJournal()

    def prepare_limit_order(self, symbol, side, quantity, price):
        order = self.guard.validate(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
        )

        exchange_info = self.client._request(
            "GET",
            "/api/v3/exchangeInfo",
            {"symbol": order["symbol"]},
            market_data=True,
        )

        validate_limit_order_filters(order, exchange_info)

        return {
            **order,
            "type": "LIMIT",
            "timeInForce": "GTC",
            "status": "VALIDATED_NOT_SUBMITTED",
        }
    
    def create_limit_order(self, *args, **kwargs):
        raise PermissionError(
            "Legacy create_limit_order is disabled. "
            "Use journal-based submission."
        )

    # def create_limit_order(
    #     self,
    #     symbol,
    #     side,
    #     quantity,
    #     price,
    #     confirmation=None,
    # ):
    #     self.guard.require_live_enabled()

    #     order = self.prepare_limit_order(
    #         symbol, side, quantity, price
    #     )

    #     if confirmation != "CONFIRM LIVE ORDER":
    #         raise PermissionError(
    #             "Explicit live order confirmation required"
    #         )

    #     client_order_id = "bot_" + uuid4().hex[:24]

    #     params = {
    #         "symbol": order["symbol"],
    #         "side": order["side"],
    #         "type": "LIMIT",
    #         "timeInForce": "GTC",
    #         "quantity": order["quantity"],
    #         "price": order["price"],
    #         "newClientOrderId": client_order_id,
    #     }

    #     return self.transport.request(
    #         "POST",
    #         "/api/v3/order",
    #         params,
    #     )

    def get_order(self, symbol, order_id):
        return self.client.get_order(
            symbol=symbol,
            order_id=order_id,
        )

    def cancel_order(
        self,
        symbol,
        order_id,
        confirmation=None,
    ):
        self.guard.require_live_enabled()

        if confirmation != "CONFIRM CANCEL ORDER":
            raise PermissionError(
                "Explicit cancellation confirmation required"
            )

        return self.transport.request(
            "DELETE",
            "/api/v3/order",
            {
                "symbol": symbol,
                "orderId": order_id,
            },
        )
    
    def prepare_order_intent(
        self,
        symbol,
        side,
        quantity,
        price,
        intent_id,
    ):
        if not intent_id or not str(intent_id).strip():
            raise ValueError("intent_id is required")

        # Validate against current Binance exchange filters.
        order = self.prepare_limit_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
        )

        # Generate once, then persist before any submission.
        client_order_id = "bot_" + uuid4().hex[:24]

        record = self.journal.create_intent(
            intent_id=str(intent_id),
            client_order_id=client_order_id,
            symbol=order["symbol"],
            side=order["side"],
            quantity=order["quantity"],
            price=order["price"],
        )

        return {
            **record,
            "notional_usdt": order["notional_usdt"],
            "submission_status": "NOT_SUBMITTED",
        }