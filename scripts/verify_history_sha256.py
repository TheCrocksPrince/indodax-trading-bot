import httpx

from app.clients.indodax_client import create_indodax_client


def main():
    client = create_indodax_client()

    endpoints = [
        ("Order History", "/api/v2/order/histories"),
        ("My Trades", "/api/v2/myTrades"),
    ]

    for name, endpoint in endpoints:
        try:
            result = client._signed_get(
                endpoint,
                {
                    "symbol": "btcidr",
                    "limit": 10,
                },
            )

            if isinstance(result, dict) and result.get("error"):
                print(name, "API ERROR", result.get("code"))
            else:
                print(name, "SUCCESS")

        except httpx.HTTPStatusError as exc:
            try:
                code = exc.response.json().get("code")
            except (ValueError, AttributeError):
                code = None

            print(name, "HTTP", exc.response.status_code, "code", code)

        except httpx.RequestError as exc:
            print(name, "NETWORK ERROR", type(exc).__name__)


if __name__ == "__main__":
    main()