
import httpx

from app.clients.binance_testnet_client import BinanceTestnetClient


def main():
    client = BinanceTestnetClient()

    try:
        print("=== BINANCE SPOT TESTNET ===")
        print("Testing LIMIT BUY BTCUSDT")

        result = client.place_limit_order(
            symbol="BTCUSDT",
            side="BUY",
            quantity="0.00010",
            price="75000.00",
            test=True,
        )

        print("TEST ORDER: PASS")
        print("Response:", result)

    except httpx.HTTPStatusError as exc:
        print("TEST ORDER: FAILED")
        print("HTTP:", exc.response.status_code)

        try:
            error = exc.response.json()
            print("Error code:", error.get("code"))
            print("Message:", error.get("msg"))
        except ValueError:
            print("Non-JSON error response")

    finally:
        client.close()


if __name__ == "__main__":
    main()
