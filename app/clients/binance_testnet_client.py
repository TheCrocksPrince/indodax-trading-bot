
import hashlib
import hmac
import os
import time
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv

load_dotenv()


class BinanceTestnetClient:
    BASE_URL = "https://testnet.binance.vision"

    def __init__(self, transport=None):
        self.api_key = os.getenv("BINANCE_TESTNET_API_KEY", "")
        self.secret = os.getenv("BINANCE_TESTNET_SECRET_KEY", "")
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            timeout=10,
            transport=transport,
            trust_env=False,
        )

    def close(self):
        self.client.close()

    def request(self, method, path, params=None, signed=True):
        
        method = method.upper()

        allowed_requests = {
            "GET": {
                "/api/v3/account",
                "/api/v3/openOrders",
                "/api/v3/allOrders",
                "/api/v3/myTrades",
                "/api/v3/order",
                "/api/v3/rateLimit/order",
                "/api/v3/exchangeInfo",
                "/api/v3/ticker/bookTicker",
            },
            "POST": {
                "/api/v3/order/test",
                "/api/v3/order",
            },
            "DELETE": {
                "/api/v3/order",
            },
        }

        if (
            method not in allowed_requests
            or path not in allowed_requests[method]
        ):
            raise PermissionError(
                "HTTP method or endpoint not allowed "
                "for Binance Spot Testnet"
            )

        params = dict(params or {})
        headers = {}

        print(
            "DEBUG:",
            "method=", method,
            "path=", path,
            "base_url=", self.BASE_URL,
            "api_key_loaded=", bool(self.api_key),
            "secret_loaded=", bool(self.secret),
        )

        if signed:
            if not self.api_key or not self.secret:
                raise RuntimeError("Missing Testnet credentials")

            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = 5000

            payload = urlencode(params)
            signature = hmac.new(
                self.secret.encode(),
                payload.encode(),
                hashlib.sha256,
            ).hexdigest()

            payload += "&signature=" + signature
            headers["X-MBX-APIKEY"] = self.api_key
        else:
            payload = urlencode(params)

        if method == "GET":
            response = self.client.request(
                method,
                path + ("?" + payload if payload else ""),
                headers=headers,
            )
        else:
            response = self.client.request(
                method,
                path,
                content=payload,
                headers={
                    **headers,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

        response.raise_for_status()
        return response.json()

    def get_account(self):
        return self.request("GET", "/api/v3/account")

    def get_open_orders(self, symbol="BTCUSDT"):
        return self.request(
            "GET", "/api/v3/openOrders",
            {"symbol": symbol},
        )

    def get_all_orders(self, symbol="BTCUSDT"):
        return self.request(
            "GET", "/api/v3/allOrders",
            {"symbol": symbol, "limit": 10},
        )

    def get_my_trades(self, symbol="BTCUSDT"):
        return self.request(
            "GET", "/api/v3/myTrades",
            {"symbol": symbol, "limit": 10},
        )

    def get_order(self, symbol, order_id):
        return self.request(
            "GET", "/api/v3/order",
            {"symbol": symbol, "orderId": order_id},
        )

    def get_order_rate_limits(self):
        return self.request(
            "GET", "/api/v3/rateLimit/order"
        )

    def test_order(self, symbol, side, quantity, price):
        return self.request(
            "POST", "/api/v3/order/test",
            {
                "symbol": symbol,
                "side": side,
                "type": "LIMIT",
                "timeInForce": "GTC",
                "quantity": str(quantity),
                "price": str(price),
            },
        )
    
    def get_exchange_info(self, symbol="BTCUSDT"):
        return self.request(
            "GET",
            "/api/v3/exchangeInfo",
            {"symbol": symbol},
            signed=False,
        )

    def place_limit_order(
        self, symbol, side, quantity, price, test=True
    ):
        if not test:
            raise RuntimeError(
                "Order submission disabled until explicitly enabled"
            )

        return self.request(
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
        )
    

    def create_limit_order(
        self, symbol, side, quantity, price, client_order_id
    ):
        if self.BASE_URL != "https://testnet.binance.vision":
            raise RuntimeError("Only Binance Spot Testnet is allowed")

        return self.request(
            "POST",
            "/api/v3/order",
            {
                "symbol": symbol,
                "side": side,
                "type": "LIMIT",
                "timeInForce": "GTC",
                "quantity": str(quantity),
                "price": str(price),
                "newClientOrderId": client_order_id,
            },
        )


    def get_order_by_client_id(self, symbol, client_order_id):
        return self.request(
            "GET",
            "/api/v3/order",
            {
                "symbol": symbol,
                "origClientOrderId": client_order_id,
            },
        )


    def cancel_order_by_client_id(self, symbol, client_order_id):
        if self.BASE_URL != "https://testnet.binance.vision":
            raise RuntimeError("Only Binance Spot Testnet is allowed")

        return self.request(
            "DELETE",
            "/api/v3/order",
            {
                "symbol": symbol,
                "origClientOrderId": client_order_id,
            },
        )
    
    def get_book_ticker(self, symbol="BTCUSDT"):
        return self.request(
            "GET",
            "/api/v3/ticker/bookTicker",
            {"symbol": symbol},
            signed=False,
        )

