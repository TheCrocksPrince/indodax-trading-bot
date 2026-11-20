import httpx

from app.clients.binance_client import BinanceClient


def main():
    client = BinanceClient(
        base_url="https://api.binance.com"
    )

    symbol = "BTCUSDT"

    checks = [
        ("Open Orders", client.get_open_orders),
        ("All Orders", client.get_all_orders),
        ("My Trades", client.get_my_trades),
    ]

    print("=== Binance Production History Check ===")
    print("Symbol:", symbol)

    passed = 0

    for name, method in checks:
        try:
            result = method(symbol)

            if not isinstance(result, list):
                raise ValueError(
                    "Unexpected response type"
                )

            print(
                "{}: PASS ({} records)".format(
                    name, len(result)
                )
            )
            passed += 1

        except httpx.HTTPStatusError as exc:
            print(
                "{}: FAILED (HTTP {})".format(
                    name, exc.response.status_code
                )
            )

        except (ValueError, RuntimeError) as exc:
            print(
                "{}: FAILED ({})".format(
                    name, type(exc).__name__
                )
            )

    print()
    print("Result: {}/3 checks passed".format(passed))


if __name__ == "__main__":
    main()