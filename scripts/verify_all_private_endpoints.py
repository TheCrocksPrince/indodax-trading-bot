
import json
import os
from datetime import datetime, timezone

from app.clients.indodax_client import create_indodax_client


def verify_endpoint(name, callback):
    try:
        response = callback()

        if not isinstance(response, (dict, list)):
            raise ValueError("Unexpected response type")

        return {
            "endpoint": name,
            "status": "LIVE_PASS",
            "response_type": type(response).__name__,
        }

    except Exception as exc:
        return {
            "endpoint": name,
            "status": "FAILED",
            "error_type": type(exc).__name__,
        }


def main():
    client = create_indodax_client()

    checks = [
        (
            "GET /api/v2/account",
            lambda: client.get_account(),
        ),
        (
            "GET /api/v2/openOrders",
            lambda: client.get_open_orders(),
        ),
        (
            "GET /api/v2/order/histories",
            lambda: client.get_order_history(
                symbol="BTCIDR",
                limit=10,
            ),
        ),
        (
            "GET /api/v2/myTrades",
            lambda: client.get_trade_history(
                symbol="BTCIDR",
                limit=10,
            ),
        ),
        (
            "GET /api/v2/capital/withdraw/history",
            lambda: client.get_coin_withdraw_history(
                coin="BTC",
                limit=10,
            ),
        ),
        (
            "GET /api/v2/capital/deposit/hisrec",
            lambda: client.get_coin_deposit_history(
                coin="BTC",
                limit=10,
            ),
        ),
        (
            "GET /api/v2/fiat/orders",
            lambda: client.get_fiat_orders(
                transaction_type="1",
                limit=10,
            ),
        ),
        (
            "GET /api/v2/capital/deposit/address/list",
            lambda: client.get_deposit_address_list(
                coin="BTC",
                network="BTC",
            ),
        ),
    ]

    results = []

    print("INDODAX PRIVATE API V2 VERIFICATION")
    print("READ-ONLY LIVE REQUESTS ONLY")
    print("=" * 50)

    for name, callback in checks:
        result = verify_endpoint(name, callback)
        results.append(result)

        print(
            "{}: {}".format(
                result["status"],
                result["endpoint"],
            )
        )

    # Requires an existing valid exchange order ID.
    order_id = os.getenv("INDODAX_VERIFY_ORDER_ID")
    order_symbol = os.getenv(
        "INDODAX_VERIFY_ORDER_SYMBOL",
        "BTCIDR",
    )

    if order_id:
        try:
            parsed_id = int(order_id)

            result = verify_endpoint(
                "GET /api/v2/order",
                lambda: client.get_order(
                    symbol=order_symbol,
                    order_id=parsed_id,
                ),
            )
        except ValueError:
            result = {
                "endpoint": "GET /api/v2/order",
                "status": "NOT_VERIFIED",
                "reason": "Invalid configured order ID",
            }
    else:
        result = {
            "endpoint": "GET /api/v2/order",
            "status": "NOT_VERIFIED",
            "reason": "No valid order ID configured",
        }

    results.append(result)
    print("{}: {}".format(result["status"], result["endpoint"]))

    mutations = [
        "POST /api/v2/order",
        "DELETE /api/v2/order",
        "POST /api/v2/capital/withdraw/apply",
        "POST /api/v2/fiat/withdraw",
    ]

    for endpoint in mutations:
        result = {
            "endpoint": endpoint,
            "status": "SIMULATED_ONLY",
            "reason": "Production mutation intentionally blocked",
        }
        results.append(result)
        print("{}: {}".format(result["status"], endpoint))

    report = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "mode": "READ_ONLY_LIVE_VERIFICATION",
        "total_endpoints": len(results),
        "results": results,
    }

    os.makedirs("reports", exist_ok=True)

    output_path = "reports/private_api_verification.json"

    with open(output_path, "w") as file:
        json.dump(report, file, indent=2)

    print("\nReport saved:", output_path)
    print("Endpoints covered:", len(results))


if __name__ == "__main__":
    main()
