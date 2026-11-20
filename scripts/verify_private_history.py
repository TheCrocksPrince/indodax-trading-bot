import argparse
import json

import httpx

from app.clients.indodax_client import create_indodax_client


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="btcidr")
    args = parser.parse_args()

    client = create_indodax_client()

    checks = [
        ("Order History", "/api/v2/order/histories"),
        ("My Trades", "/api/v2/myTrades"),
    ]

    for name, endpoint in checks:
        try:
            result = client._signed_get_sha512(
                endpoint,
                {
                    "symbol": args.symbol.lower(),
                    "limit": 10,
                },
                base_url=client.base_url,
            )

            if isinstance(result, dict) and result.get("error"):
                print(
                    "{}: API ERROR {}".format(
                        name,
                        result.get("code", "unknown"),
                    )
                )
                continue

            if isinstance(result, dict):
                records = result.get("data", [])
            elif isinstance(result, list):
                records = result
            else:
                raise ValueError("Unexpected response")

            print(
                "{}: SUCCESS ({} records)".format(
                    name,
                    len(records),
                )
            )

        except httpx.HTTPStatusError as exc:
            print(
                "{}: HTTP {}".format(
                    name,
                    exc.response.status_code,
                )
            )
            try:
                payload = exc.response.json()
                print(
                    "API error code:",
                    payload.get("code", "unknown"),
                )
                print(
                    "API message:",
                    str(payload.get("error", "unknown"))[:200],
                )
            except (ValueError, AttributeError):
                print("Non-JSON error response")

        except httpx.RequestError as exc:
            print(
                "{}: NETWORK ERROR ({})".format(
                    name,
                    type(exc).__name__,
                )
            )


if __name__ == "__main__":
    main()