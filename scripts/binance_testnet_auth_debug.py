
import hashlib
import hmac
import os
import time
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("BINANCE_TESTNET_API_KEY", "")
secret = os.getenv("BINANCE_TESTNET_SECRET_KEY", "")

if not api_key or not secret:
    raise RuntimeError("Missing Testnet credentials")

params = {
    "timestamp": int(time.time() * 1000),
    "recvWindow": 5000,
}

payload = urlencode(params)

signature = hmac.new(
    secret.encode("utf-8"),
    payload.encode("utf-8"),
    hashlib.sha256,
).hexdigest()

url = (
    "https://testnet.binance.vision"
    "/api/v3/account"
    "?" + payload
    + "&signature=" + signature
)

with httpx.Client(
    timeout=10,
    trust_env=False,
) as client:
    response = client.get(
        url,
        headers={
            "X-MBX-APIKEY": api_key,
        },
    )

print("HTTP status:", response.status_code)

try:
    result = response.json()

    if response.is_success:
        print("AUTHENTICATION: PASS")
        print("Account type:", result.get("accountType"))
        print("Can trade:", result.get("canTrade"))
    else:
        print("Error code:", result.get("code"))
        print("Error message:", result.get("msg"))

except ValueError:
    print("Non-JSON response")
