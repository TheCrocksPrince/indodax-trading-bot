
import httpx

from app.clients.binance_testnet_client import BinanceTestnetClient


def main():
    client = BinanceTestnetClient()

    try:
        account = client.get_account()

        print("BINANCE TESTNET ACCOUNT: PASS")
        print("Can trade:", account.get("canTrade"))
        print("Account type:", account.get("accountType"))
        print("Balance entries:", len(account.get("balances", [])))

        for name, method in [
            ("Open orders", client.get_open_orders),
            ("All orders", client.get_all_orders),
            ("My trades", client.get_my_trades),
            ("Order rate limits", client.get_order_rate_limits),
        ]:
            try:
                result = method()
                print(name, "PASS", "items:", len(result))
            except httpx.HTTPStatusError as exc:
                print(
                    name, "HTTP ERROR",
                    exc.response.status_code,
                    exc.response.text[:300],
                )

    except httpx.HTTPStatusError as exc:
        print("AUTH/API ERROR:", exc.response.status_code)
        print(exc.response.text[:300])

    except httpx.RequestError as exc:
        print("NETWORK ERROR:", type(exc).__name__)

    finally:
        client.close()


if __name__ == "__main__":
    main()
