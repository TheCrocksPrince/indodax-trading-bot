import httpx

from scripts.binance_order_journal import (
    InvalidOrderTransitionError,
)

from app.services.binance_execution_guard import (
    BinanceExecutionGuard,
)


class BinanceOrderSubmission:
    def __init__(self, journal, transport, guard=None):
        if journal is None or transport is None:
            raise ValueError(
                "Journal and transport are required"
            )

        self.journal = journal
        self.transport = transport
        self.guard = guard or BinanceExecutionGuard()

    def submit_prepared_intent(self, intent_id):
        record = self.journal.get_intent(intent_id)

        if record is None:
            raise ValueError("Order intent not found")
        
        # Final validation before claiming the intent.
        self.guard.validate(
            symbol=record["symbol"],
            side=record["side"],
            quantity=record["quantity"],
            price=record["price"],
        )

        # Atomic claim. Duplicate submissions fail here.
        self.journal.claim_for_submission(intent_id)

        params = {
            "symbol": record["symbol"],
            "side": record["side"],
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": record["quantity"],
            "price": record["price"],
            "newClientOrderId": record["client_order_id"],
        }

        try:
            response = self.transport.request(
                "POST",
                "/api/v3/order",
                params,
            )

        except httpx.HTTPStatusError as exc:
            # Only an explicit, unambiguous exchange rejection
            # should eventually become REJECTED.
            # Until classified, preserve UNKNOWN.
            self.journal.transition(
                intent_id,
                "SUBMITTING",
                "UNKNOWN",
                error_message=(
                    "HTTP response requires reconciliation"
                ),
            )
            raise

        except Exception:
            # Timeout, network failure, or unexpected response.
            # Never retry automatically.
            self.journal.transition(
                intent_id,
                "SUBMITTING",
                "UNKNOWN",
                error_message=(
                    "Submission outcome is uncertain"
                ),
            )
            raise

        if (
            not isinstance(response, dict)
            or response.get("orderId") is None
            or response.get("symbol") != record["symbol"]
            or response.get("clientOrderId")
            != record["client_order_id"]
        ):
            self.journal.transition(
                intent_id,
                "SUBMITTING",
                "UNKNOWN",
                error_message="Unverified exchange response",
            )
            raise RuntimeError(
                "Exchange response could not be verified"
            )

        updated = self.journal.transition(
            intent_id,
            "SUBMITTING",
            "ACKNOWLEDGED",
            exchange_order_id=response["orderId"],
        )

        return {
            "intent_id": intent_id,
            "client_order_id": record["client_order_id"],
            "journal_status": updated["status"],
            "exchange_status": response.get("status"),
            "exchange_order_id": response["orderId"],
        }