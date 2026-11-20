
import httpx

from app.clients.indodax_client import create_indodax_client


def verify(name, operation):
    print("\n" + name)

    try:
        result = operation()

        print("Request: SUCCESS")

        if isinstance(result, list):
            print("Records:", len(result))
        elif isinstance(result, dict):
            print("Response type: dict")
            if isinstance(result.get("data"), list):
                print("Records:", len(result["data"]))
        else:
            print("Response type:", type(result).__name__)

    except httpx.HTTPStatusError as exc:
        print("HTTP status:", exc.response.status_code)

        try:
            body = exc.response.json()
            if isinstance(body, dict):
                print("API error code:", body.get("code", "N/A"))
        except ValueError:
            pass

    except Exception as exc:
        print("Error type:", type(exc).__name__)


def main():
    client = create_indodax_client()

    verify(
        "Coin Withdrawal History",
        lambda: client.get_coin_withdraw_history(
            coin="BTC",
            limit=10,
        ),
    )

    verify(
        "Coin Deposit History",
        lambda: client.get_coin_deposit_history(
            coin="BTC",
            limit=10,
        ),
    )


    verify(
        "Fiat Withdrawal History",
        lambda: client.get_fiat_orders(
            transaction_type="1",
            limit=10,
        ),
    )

    verify(
        "Fiat Deposit History",
        lambda: client.get_fiat_orders(
            transaction_type="0",
            limit=10,
        ),
    )

    verify(
        "BTC Deposit Address List",
        lambda: client.get_deposit_address_list(
            coin="BTC",
            network="BTC",
        ),
    )



if __name__ == "__main__":
    main()
