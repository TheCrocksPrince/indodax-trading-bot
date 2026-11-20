
import hashlib
import hmac
import os
import time
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv

load_dotenv()


class BinanceClient:
    def __init__(
        self,
        base_url=None,
        timeout=10.0,
        api_key=None,
        secret_key=None,
        read_only = True,
    ):
        if read_only is not True:
            raise PermissionError(
                "BinanceClient is permanently read-only. "
                "Use a separately authorized execution client."
            )

        self.read_only = True
        
        self.base_url = (
            base_url
            or os.getenv(
                "BINANCE_BASE_URL",
                "https://api.binance.com",
            )
        ).rstrip("/")

        self.market_url = "https://data-api.binance.vision"
        self.timeout = timeout
        self.api_key = (
            api_key if api_key is not None
            else os.getenv("BINANCE_API_KEY", "")
        )
        self.secret_key = (
            secret_key if secret_key is not None
            else os.getenv("BINANCE_SECRET_KEY", "")
        )

    def _request(
        self,
        method,
        endpoint,
        params=None,
        signed=False,
        market_data=False,
    ):
        method = method.upper()

        # Safety guard: block all non-GET requests
        if method != "GET":
            raise PermissionError(
                "Binance production is READ-ONLY. "
                "POST, PUT, PATCH, and DELETE requests are disabled."
            )

        # Allow only explicitly approved GET endpoints
        allowed_endpoints = {
            "/api/v3/ping",
            "/api/v3/time",
            "/api/v3/exchangeInfo",
            "/api/v3/ticker/bookTicker",
            "/api/v3/depth",
            "/api/v3/account",
            "/api/v3/openOrders",
            "/api/v3/allOrders",
            "/api/v3/myTrades",
            "/api/v3/order",
            "/api/v3/rateLimit/order",
            "/sapi/v1/capital/config/getall",
            "/sapi/v1/capital/deposit/hisrec",
            "/sapi/v1/capital/withdraw/history",
        }

        if endpoint not in allowed_endpoints:
            raise PermissionError(
                "Endpoint is not allowlisted for read-only access"
            )

        params = dict(params or {})
        headers = {"Accept": "application/json"}

        # Keep your existing signing and HTTP request code below.

        if signed:
            if not self.api_key or not self.secret_key:
                raise RuntimeError(
                    "Missing Binance API credentials"
                )

            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = 5000

            payload = urlencode(params)

            signature = hmac.new(
                self.secret_key.encode("utf-8"),
                payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            params["signature"] = signature
            headers["X-MBX-APIKEY"] = self.api_key

        url = (
            self.market_url if market_data
            else self.base_url
        ) + endpoint

        with httpx.Client(
            timeout=self.timeout,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            response = client.request(
                method,
                url,
                params=params if method == "GET" else None,
                data=params if method != "GET" else None,
                headers=headers,
            )

            response.raise_for_status()
            return response.json()

    # Public market data
    def ping(self):
        return self._request(
            "GET", "/api/v3/ping", market_data=True
        )

    def get_book_ticker(self, symbol="BTCUSDT"):
        return self._request(
            "GET",
            "/api/v3/ticker/bookTicker",
            {"symbol": symbol.upper()},
            market_data=True,
        )

    def get_order_book(self, symbol="BTCUSDT", limit=5):
        return self._request(
            "GET",
            "/api/v3/depth",
            {"symbol": symbol.upper(), "limit": limit},
            market_data=True,
        )

    # Signed account and trading queries
    def get_account(self):
        return self._request(
            "GET", "/api/v3/account", signed=True
        )

    def get_open_orders(self, symbol="BTCUSDT"):
        return self._request(
            "GET",
            "/api/v3/openOrders",
            {"symbol": symbol},
            signed=True,
        )

    def get_all_orders(self, symbol="BTCUSDT"):
        return self._request(
            "GET",
            "/api/v3/allOrders",
            {"symbol": symbol, "limit": 10},
            signed=True,
        )

    def get_my_trades(self, symbol="BTCUSDT"):
        return self._request(
            "GET",
            "/api/v3/myTrades",
            {"symbol": symbol, "limit": 10},
            signed=True,
        )

    def get_order(self, symbol, order_id):
        return self._request(
            "GET",
            "/api/v3/order",
            {"symbol": symbol, "orderId": order_id},
            signed=True,
        )

    def get_order_rate_limits(self):
        return self._request(
            "GET",
            "/api/v3/rateLimit/order",
            signed=True,
        )

    def get_capital_config(self):
        return self._request(
            "GET",
            "/sapi/v1/capital/config/getall",
            signed=True,
        )

    def get_deposit_history(self):
        return self._request(
            "GET",
            "/sapi/v1/capital/deposit/hisrec",
            {"limit": 10},
            signed=True,
        )

    def get_withdraw_history(self):
        return self._request(
            "GET",
            "/sapi/v1/capital/withdraw/history",
            {"limit": 10},
            signed=True,
        )

    def test_order(self, symbol, side, quantity, price):
        return self._request(
            "POST",
            "/api/v3/order/test",
            {
                "symbol": symbol,
                "side": side,
                "type": "LIMIT",
                "timeInForce": "GTC",
                "quantity": str(quantity),
                "price": str(price),
            },
            signed=True,
        )
    
    def get_server_time(self):
        return self._request(
            "GET",
            "/api/v3/time",
        )

    def get_exchange_info(self, symbol="BTCUSDT"):
        return self._request(
            "GET",
            "/api/v3/exchangeInfo",
            {"symbol": symbol.upper()},
        )
    
    def get_order_by_client_id(
        self,
        symbol: str,
        client_order_id: str,
    ):
        """
        Retrieve an existing Binance Spot order.

        Read-only signed GET request.
        Does not create, cancel, or modify orders.
        """

        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("symbol is required")

        if (
            not isinstance(client_order_id, str)
            or not client_order_id.strip()
        ):
            raise ValueError("client_order_id is required")

        symbol = symbol.strip().upper()
        client_order_id = client_order_id.strip()

        if not (
            symbol.isascii()
            and symbol.isalnum()
            and 2 <= len(symbol) <= 20
        ):
            raise ValueError("Invalid Binance symbol")

        if not (
            1 <= len(client_order_id) <= 36
            and all(
                ch.isascii()
                and (ch.isalnum() or ch in "_-.")
                for ch in client_order_id
            )
        ):
            raise ValueError("Invalid client_order_id")

        return self._request(
            "GET",
            "/api/v3/order",
            {
                "symbol": symbol,
                "origClientOrderId": client_order_id,
            },
            signed=True,
        )
