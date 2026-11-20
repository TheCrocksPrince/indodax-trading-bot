class BinanceOrderReconciliation:
    """
    Read-only exchange reconciliation.

    The lookup client must provide:
        get_order_by_client_id(symbol, client_order_id)
    """

    def __init__(self, journal, lookup_client):
        if journal is None or lookup_client is None:
            raise ValueError(
                "Journal and lookup client are required"
            )

        self.journal = journal
        self.lookup_client = lookup_client

    def reconcile(self, intent_id, recover_stale=False):
        record = self.journal.get_intent(intent_id)

        if record is None:
            raise ValueError("Order intent not found")

        status = record["status"]

        if status == "ACKNOWLEDGED":
            return {
                "intent_id": intent_id,
                "status": "ACKNOWLEDGED",
                "action": "ALREADY_RECONCILED",
            }

        if status not in ("UNKNOWN", "SUBMITTING"):
            raise ValueError(
                "Order is not eligible for reconciliation"
            )

        if status == "SUBMITTING":
            if not recover_stale:
                raise RuntimeError(
                    "SUBMITTING may still be in flight. "
                    "Explicit recovery is required."
                )

            # Only invoke after the previous submission
            # worker is confirmed stopped.
            self.journal.transition(
                intent_id,
                "SUBMITTING",
                "UNKNOWN",
                error_message="Recovery requested",
            )

        try:
            response = (
                self.lookup_client.get_order_by_client_id(
                    symbol=record["symbol"],
                    client_order_id=record["client_order_id"],
                )
            )
        except Exception:
            # Includes timeouts, API errors and order-not-found.
            # None of these proves the order was rejected.
            return {
                "intent_id": intent_id,
                "status": "UNKNOWN",
                "action": "RETRY_LOOKUP_LATER",
            }

        if not isinstance(response, dict):
            return self._unverified(intent_id)

        if (
            response.get("symbol") != record["symbol"]
            or response.get("clientOrderId")
            != record["client_order_id"]
            or response.get("orderId") is None
            or response.get("status") is None
        ):
            return self._unverified(intent_id)

        # A valid order response proves the exchange
        # knows about the order, not that it was filled.
        self.journal.transition(
            intent_id,
            "UNKNOWN",
            "ACKNOWLEDGED",
            exchange_order_id=response["orderId"],
        )

        return {
            "intent_id": intent_id,
            "status": "ACKNOWLEDGED",
            "action": "ORDER_FOUND",
            "exchange_order_id": response["orderId"],
            "exchange_status": response["status"],
        }

    def _unverified(self, intent_id):
        return {
            "intent_id": intent_id,
            "status": "UNKNOWN",
            "action": "UNVERIFIED_RESPONSE",
        }