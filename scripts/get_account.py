import json

from app.clients.indodax_client import create_indodax_client


def main():
    client = create_indodax_client()

    account = client.get_account(
        omit_zero_balances=True
    )

    print(
        json.dumps(
            account,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()