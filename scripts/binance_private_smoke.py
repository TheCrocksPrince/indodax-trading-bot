
import json
import httpx

from app.clients.binance_client import BinanceClient


def main():
    client = BinanceClient()

    checks = [
        ("account", client.get_account),
        ("open_orders", client.get_open_orders),
        ("all_orders", client.get_all_orders),
        ("my_trades", client.get_my_trades),
        ("order_rate_limits", client.get_order_rate_limits),
        ("capital_config", client.get_capital_config),
        ("deposit_history", client.get_deposit_history),
        ("withdraw_history", client.get_withdraw_history),
    ]

    results = []

    for name, fn in checks:
        print("Testing:", name)

        try:
            result = fn()
            status = "PASS"
            detail = (
                "items={}".format(len(result))
                if isinstance(result, list)
                else "keys={}".format(
                    list(result.keys())[:8]
                )
            )

        except httpx.ConnectError as exc:
            message = str(exc).lower()

            if any(x in message for x in (
                "certificate",
                "ssl",
                "tls",
            )):
                status = "TLS_ERROR"
            else:
                status = "CONNECT_ERROR"

            detail = type(exc).__name__

        except httpx.ConnectError:
            status = "BLOCKED_NETWORK"
            detail = "Connection failed"

        except httpx.TimeoutException:
            status = "TIMEOUT"
            detail = "Request timed out"

        except httpx.HTTPStatusError as exc:
            status = "HTTP_ERROR"
            detail = "HTTP {}".format(
                exc.response.status_code
            )
            try:
                error = exc.response.json()
                detail += " code={} msg={}".format(
                    error.get("code"),
                    error.get("msg"),
                )
            except (ValueError, AttributeError):
                pass

            if exc.response.status_code in (418, 429):
                results.append({
                    "endpoint": name,
                    "status": status,
                    "detail": detail,
                })
                print(status, detail)
                break

        except Exception as exc:
            status = "ERROR"
            detail = type(exc).__name__

        print(status, detail)
        results.append({
            "endpoint": name,
            "status": status,
            "detail": detail,
        })

    with open(
        "binance_private_results.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(results, file, indent=2)

    print("\nResults saved.")


if __name__ == "__main__":
    main()
