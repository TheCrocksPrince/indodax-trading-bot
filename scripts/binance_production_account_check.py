import httpx

from app.clients.binance_client import BinanceClient


def main():
    client = BinanceClient(
        base_url="https://api.binance.com"
    )

    try:
        account = client.get_account()

        # Only print non-sensitive status fields
        print("=== Binance Production Account Check ===")
        print("Can Trade:", account.get("canTrade"))
        print("Can Withdraw:", account.get("canWithdraw"))
        print("Can Deposit:", account.get("canDeposit"))
        print("Account Type:", account.get("accountType"))
        print("Authentication: PASS")

    except httpx.HTTPStatusError as exc:
        print("Authentication: FAILED")
        print("HTTP Status:", exc.response.status_code)
        # Do not print request headers or signed URLs.


if __name__ == "__main__":
    main()