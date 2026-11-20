import hashlib
import hmac
import time
from urllib.parse import urlencode

import httpx

from app.clients.binance_client import BinanceClient


class BinanceExecutionTransport:
    def __init__(self, client=None, http_client=None):
        self.client = client or BinanceClient()
        self.http_client = http_client

    # def request(self, method, endpoint, params=None):
    #     method = method.upper()
    def request(self, method, endpoint, params=None):
        # Temporary production execution lock.
        # Do not remove until journal-bound authorization,
        # risk validation and reconciliation are complete.
        raise PermissionError(
            "Binance production execution is locked. "
            "POST/DELETE requests are not permitted."
        )

        if method not in {"POST", "DELETE"}:
            raise PermissionError("Unsupported execution method")

        if endpoint != "/api/v3/order":
            raise PermissionError("Execution endpoint not allowed")

        if not self.client.api_key or not self.client.secret_key:
            raise RuntimeError("Missing Binance API credentials")

        params = dict(params or {})
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = 5000

        payload = urlencode(params)

        signature = hmac.new(
            self.client.secret_key.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        params["signature"] = signature

        headers = {
            "X-MBX-APIKEY": self.client.api_key,
            "Accept": "application/json",
        }

        url = self.client.base_url + endpoint

        if self.http_client is not None:
            response = self.http_client.request(
                method,
                url,
                data=params,
                headers=headers,
            )
        else:
            with httpx.Client(
                timeout=self.client.timeout,
                follow_redirects=False,
                trust_env=False,
            ) as http_client:
                response = http_client.request(
                    method,
                    url,
                    data=params,
                    headers=headers,
                )

        response.raise_for_status()
        return response.json()