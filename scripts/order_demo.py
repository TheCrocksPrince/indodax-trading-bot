
from pprint import pprint

from app.clients.indodax_client import IndodaxClient


client = IndodaxClient(
    api_key="demo-key",
    secret_key="demo-secret",
)

print("=== CREATE ORDER DRY RUN ===")
created = client.create_order(
    symbol="BTCIDR",
    side="BUY",
    price="1000000000",
    quantity="0.00001",
)
pprint(created)

print("\n=== CANCEL ORDER DRY RUN ===")
cancelled = client.cancel_order(
    symbol="BTCIDR",
    order_id=12345,
)
pprint(cancelled)
