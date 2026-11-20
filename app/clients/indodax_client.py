import time

import httpx
from typing import Optional

from app.auth.signer import IndodaxSigner
from app.config.settings import settings
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from app.clients.withdrawal_journal import WithdrawalJournal

import json
import socket

from app.clients.withdrawal_safety import (
    check_crypto_destination,
    check_idr_destination,
    check_live_withdrawal_enabled,
)


class IndodaxClient:
    """
    HTTP client for Indodax Trade API v2.
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        base_url: str = "https://api.indodax.com",
        recv_window: int = 5000,
    ):
        self.api_key = api_key
        self.signer = IndodaxSigner(secret_key)
        self.base_url = base_url.rstrip("/")
        self.recv_window = recv_window

    def _build_signed_params(
        self,
        params: Optional[dict] = None,
    ) -> dict:
        params = dict(params or {})

        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = self.recv_window

        return params

    def _build_headers(self, signature: str) -> dict:
        return {
            "Accept": "application/json",
            "X-APIKEY": self.api_key,
            "Sign": signature,
        }

    def get_account(
        self,
        omit_zero_balances: bool = False,
    ) -> dict:

        params = self._build_signed_params(
            {
                "omitZeroBalances": str(
                    omit_zero_balances
                ).lower()
            }
        )

        signature = self.signer.sign(params)

        headers = self._build_headers(signature)

        response = httpx.get(
            f"{self.base_url}/api/v2/account",
            params=params,
            headers=headers,
            timeout=10.0,
        )

        if not response.is_success:
            print("HTTP Status:", response.status_code)
            print("Indodax Response:", response.text)

        if response.status_code == 403:
            print("\n=== AUTH DEBUG ===")
            print("Status:", response.status_code)
            print("Server:", response.headers.get("server"))
            print("CF-Ray:", response.headers.get("cf-ray"))
            print("Via:", response.headers.get("via"))
            print("Response:", response.text)

            # Public IP: IP yang terlihat dari internet
            try:
                with httpx.Client(timeout=5, trust_env=False) as ip_client:
                    ip_response = ip_client.get("https://api.ipify.org")
                    ip_response.raise_for_status()
                    print("Public IPv4:", ip_response.text.strip())
            except Exception as exc:
                print("Public IPv4: unavailable", type(exc).__name__)

            # DNS: seluruh IP gateway yang tersedia
            try:
                addresses = sorted({
                    item[4][0]
                    for item in socket.getaddrinfo(
                        "api.indodax.com",
                        443,
                        type=socket.SOCK_STREAM,
                    )
                })
                print("Gateway DNS IPs:", addresses)
            except OSError as exc:
                print("Gateway DNS: unavailable", type(exc).__name__)

            # IP peer: gateway yang digunakan oleh request ini
            stream = response.extensions.get("network_stream")

            if stream is not None:
                try:
                    print("Connected Gateway IP:", stream.get_extra_info("server_addr"))
                    print("Local Socket IP:", stream.get_extra_info("client_addr"))
                except Exception as exc:
                    print("Socket IP: unavailable", type(exc).__name__)
            else:
                print("Connected Gateway IP: unavailable")

            print("==================\n")

        response.raise_for_status()
        return response.json()
    

    def get_open_orders(self, symbol=None) -> dict:
        """
        Mengambil pending orders dari Indodax Trade API V2.

        Endpoint: GET /api/v2/openOrders
        symbol bersifat opsional, misalnya BTCIDR.
        """
        params = {}

        if symbol is not None:
            symbol = symbol.strip().upper()

            if not symbol or not symbol.isalnum():
                raise ValueError("Invalid symbol format")

            params["symbol"] = symbol

        params = self._build_signed_params(params)
        signature = self.signer.sign(params)
        headers = self._build_headers(signature)

        response = httpx.get(
            "{}/api/v2/openOrders".format(self.base_url),
            params=params,
            headers=headers,
            timeout=10.0,
        )

        if not response.is_success:
            print("HTTP Status:", response.status_code)
            print("Indodax Response:", response.text)

        response.raise_for_status()
        data = response.json()

        if not isinstance(data, (dict, list)):
            raise ValueError("Unexpected open orders response format")

        return data
    
    
    def create_order(
        self,
        symbol: str,
        side: str,
        price=None,
        quantity=None,
        time_in_force: str = "GTC",
        dry_run: bool = True,
        order_type: str = "LIMIT",
        quote_order_qty=None,
    ) -> dict:
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("Invalid symbol")
        if not isinstance(side, str):
            raise ValueError("Invalid side")
        if not isinstance(order_type, str):
            raise ValueError("Invalid order type")
        if not isinstance(time_in_force, str):
            raise ValueError("Invalid timeInForce")

        symbol = symbol.strip().upper()
        side = side.strip().upper()
        order_type = order_type.strip().upper()
        time_in_force = time_in_force.strip().upper()

        if not symbol.isascii() or not symbol.isalnum():
            raise ValueError("Invalid symbol")
        if side not in ("BUY", "SELL"):
            raise ValueError("Side must be BUY or SELL")
        if order_type not in ("LIMIT", "MARKET"):
            raise ValueError("Order type must be LIMIT or MARKET")
        if time_in_force not in ("GTC", "MOC"):
            raise ValueError("Invalid timeInForce")

        def positive_decimal(value, field_name):
            if isinstance(value, bool):
                raise ValueError("Invalid {}".format(field_name))
            try:
                number = Decimal(str(value))
            except (InvalidOperation, TypeError, ValueError):
                raise ValueError("Invalid {}".format(field_name))

            if not number.is_finite() or number <= 0:
                raise ValueError(
                    "{} must be positive and finite".format(field_name)
                )
            return number

        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
        }

        if order_type == "LIMIT":
            if price is None or quantity is None:
                raise ValueError(
                    "LIMIT order requires price and quantity"
                )
            if quote_order_qty is not None:
                raise ValueError(
                    "LIMIT order cannot use quoteOrderQty"
                )

            params["price"] = str(positive_decimal(price, "price"))
            params["quantity"] = str(
                positive_decimal(quantity, "quantity")
            )
            params["timeInForce"] = time_in_force

        elif side == "BUY":
            if price is not None or quantity is not None:
                raise ValueError(
                    "MARKET BUY requires quoteOrderQty only"
                )
            if time_in_force != "GTC":
                raise ValueError(
                    "timeInForce is not supported for MARKET orders"
                )

            quote_amount = positive_decimal(
                quote_order_qty,
                "quoteOrderQty",
            )

            if quote_amount != quote_amount.to_integral_value():
                raise ValueError(
                    "quoteOrderQty must be an integer IDR amount"
                )

            params["quoteOrderQty"] = str(int(quote_amount))

        else:
            if price is not None or quote_order_qty is not None:
                raise ValueError(
                    "MARKET SELL requires quantity only"
                )
            if time_in_force != "GTC":
                raise ValueError(
                    "timeInForce is not supported for MARKET orders"
                )

            params["quantity"] = str(
                positive_decimal(quantity, "quantity")
            )

        signed_params = self._build_signed_params(params)
        signature = self.signer.sign(signed_params)
        headers = self._build_headers(signature)

        if dry_run:
            return {
                "mode": "DRY_RUN",
                "method": "POST",
                "endpoint": "/api/v2/order",
                "params": {
                    key: value
                    for key, value in signed_params.items()
                    if key not in ("signature", "Sign")
                },
                "signed": True,
                "sent": False,
            }

        response = httpx.post(
            "{}/api/v2/order".format(self.base_url),
            data=signed_params,
            headers={
                **headers,
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=10.0,
            follow_redirects=False,
        )

        response.raise_for_status()
        return response.json()

    def cancel_order(
        self,
        symbol: str,
        order_id: int,
        dry_run: bool = True,
    ) -> dict:
        
        symbol = symbol.strip().upper()

        if not symbol.isalnum():
            raise ValueError("Invalid symbol")
        
        import re

        if isinstance(order_id, bool):
            raise ValueError("Invalid order ID")

        if isinstance(order_id, int):
            if order_id <= 0:
                raise ValueError("Invalid order ID")

        elif isinstance(order_id, str):
            order_id = order_id.strip()

            if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", order_id):
                raise ValueError("Invalid order ID")

        else:
            raise ValueError("Invalid order ID")

        params = self._build_signed_params({
            "symbol": symbol,
            "orderId": order_id,
        })
        signature = self.signer.sign(params)
        headers = self._build_headers(signature)

        if dry_run:
            return {
                "mode": "DRY_RUN",
                "method": "DELETE",
                "endpoint": "/api/v2/order",
                "params": params,
                "signed": True,
                "sent": False,
            }

        response = httpx.delete(
            f"{self.base_url}/api/v2/order",
            params=params,
            headers=headers,
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()
    

    def _signed_get(self, endpoint, params):
        params = self._build_signed_params(params)
        signature = self.signer.sign(params)

        response = httpx.get(
            f"{self.base_url}{endpoint}",
            params=params,
            headers=self._build_headers(signature),
            timeout=10.0,
        )
        response.raise_for_status()

        data = response.json()
        if not isinstance(data, (dict, list)):
            raise ValueError("Unexpected API response format")
        return data

    def get_order(self, symbol, order_id):
        symbol = symbol.strip().upper()

        if not symbol.isalnum():
            raise ValueError("Invalid symbol")
        import re

        if isinstance(order_id, bool):
            raise ValueError("Invalid order ID")

        if isinstance(order_id, int):
            if order_id <= 0:
                raise ValueError("Invalid order ID")

        elif isinstance(order_id, str):
            order_id = order_id.strip()

            if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", order_id):
                raise ValueError("Invalid order ID")

        else:
            raise ValueError("Invalid order ID")

        return self._signed_get(
            "/api/v2/order",
            {
                "symbol": symbol,
                "orderId": order_id,
            },
        )
    
    @staticmethod
    def _history_params(
        symbol,
        limit,
        start_time=None,
        end_time=None,
        sort="desc",
    ):
        if not isinstance(symbol, str):
            raise ValueError("Invalid symbol")

        symbol = symbol.strip().upper()

        if not symbol or not symbol.isascii() or not symbol.isalnum():
            raise ValueError("Invalid symbol")

        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ValueError("Invalid limit")

        if not 10 <= limit <= 1000:
            raise ValueError("Limit must be between 10 and 1000")

        if sort not in ("asc", "desc"):
            raise ValueError("Sort must be asc or desc")

        params = {
            "symbol": symbol,
            "limit": limit,
            "sort": sort,
        }

        for name, value in (
            ("startTime", start_time),
            ("endTime", end_time),
        ):
            if value is not None:
                if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value < 0
                ):
                    raise ValueError("Invalid {}".format(name))

                params[name] = value

        if start_time is not None and end_time is not None:
            if start_time > end_time:
                raise ValueError("startTime must be <= endTime")

            seven_days_ms = 7 * 24 * 60 * 60 * 1000

            if end_time - start_time > seven_days_ms:
                raise ValueError("History range cannot exceed 7 days")

        return params
    
    def get_order_history(
        self,
        symbol,
        limit=100,
        start_time=None,
        end_time=None,
        sort="desc",
    ):
        params = self._history_params(
            symbol,
            limit,
            start_time,
            end_time,
            sort,
        )

        return self._signed_get(
            "/api/v2/order/histories",
            params,
        )

    def get_trade_history(
        self,
        symbol,
        limit=100,
        start_time=None,
        end_time=None,
        sort="desc",
        order_id=None,
        client_order_id=None,
    ):
        params = self._history_params(
            symbol,
            limit,
            start_time,
            end_time,
            sort,
        )

        if order_id is not None and client_order_id is not None:
            raise ValueError(
                "Use order_id or client_order_id, not both"
            )

        if order_id is not None:
            if not isinstance(order_id, str) or not order_id.strip():
                raise ValueError("Invalid order_id")
            params["orderId"] = order_id.strip()

        if client_order_id is not None:
            if (
                not isinstance(client_order_id, str)
                or not client_order_id.strip()
            ):
                raise ValueError("Invalid client_order_id")

            params["clientOrderId"] = client_order_id.strip()

        return self._signed_get(
            "/api/v2/myTrades",
            params,
        )
    

    @staticmethod
    def _validate_coin(coin):
        if not isinstance(coin, str):
            raise ValueError("Invalid coin")

        coin = coin.strip().upper()

        if not coin or not coin.isascii() or not coin.isalnum():
            raise ValueError("Invalid coin")

        return coin

    @staticmethod
    def _validate_history_range(start_time, end_time, max_days):
        for value in (start_time, end_time):
            if value is not None:
                if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value < 0
                ):
                    raise ValueError("Invalid timestamp")

        if start_time is not None and end_time is not None:
            if start_time > end_time:
                raise ValueError("Start time exceeds end time")

            max_range = max_days * 24 * 60 * 60 * 1000

            if end_time - start_time > max_range:
                raise ValueError(
                    "History range exceeds {} days".format(max_days)
                )

    @staticmethod
    def _validate_limit(limit):
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ValueError("Invalid limit")

        if not 10 <= limit <= 1000:
            raise ValueError("Limit must be between 10 and 1000")

    def get_coin_withdraw_history(
        self,
        coin="BTC",
        start_time=None,
        end_time=None,
        limit=1000,
        status=None,
    ):
        self._validate_limit(limit)
        self._validate_history_range(start_time, end_time, 90)

        params = {
            "coin": self._validate_coin(coin),
            "limit": limit,
        }

        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        if status is not None:
            if not isinstance(status, str) or not status.strip():
                raise ValueError("Invalid withdrawal status")
            params["WithdrawStatus"] = status.strip()

        return self._signed_get(
            "/api/v2/capital/withdraw/history",
            params,
        )

    def get_coin_deposit_history(
        self,
        coin="BTC",
        start_time=None,
        end_time=None,
        limit=1000,
        status=None,
    ):
        self._validate_limit(limit)
        self._validate_history_range(start_time, end_time, 90)

        params = {
            "coin": self._validate_coin(coin),
            "limit": limit,
        }

        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        if status is not None:
            if not isinstance(status, str) or not status.strip():
                raise ValueError("Invalid deposit status")
            params["depositStatus"] = status.strip()

        return self._signed_get(
            "/api/v2/capital/deposit/hisrec",
            params,
        )

    def get_fiat_orders(
        self,
        transaction_type="1",
        begin_time=None,
        end_time=None,
        limit=1000,
    ):
        if transaction_type not in ("0", "1"):
            raise ValueError("transaction_type must be '0' or '1'")

        self._validate_limit(limit)
        self._validate_history_range(begin_time, end_time, 30)

        params = {
            "transactionType": transaction_type,
            "limit": limit,
        }

        if begin_time is not None:
            params["beginTime"] = begin_time
        if end_time is not None:
            params["endTime"] = end_time

        return self._signed_get(
            "/api/v2/fiat/orders",
            params,
        )

    def get_deposit_address_list(self, coin, network):
        coin = self._validate_coin(coin)

        if not isinstance(network, str):
            raise ValueError("Invalid network")

        network = network.strip()

        if not network or not network.isascii() or not network.isalnum():
            raise ValueError("Invalid network")

        return self._signed_get(
            "/api/v2/capital/deposit/address/list",
            {
                "coin": coin,
                "network": network,
            },
        )
    

    @staticmethod
    def _validate_withdraw_amount(amount):
        from decimal import Decimal, InvalidOperation

        if not isinstance(amount, str):
            raise ValueError("Crypto withdrawal amount must be a string")

        if not amount or amount.strip() != amount:
            raise ValueError("Invalid withdrawal amount")

        try:
            value = Decimal(amount)
        except InvalidOperation:
            raise ValueError("Invalid withdrawal amount")

        if not value.is_finite() or value <= 0:
            raise ValueError("Withdrawal amount must be positive")

        return amount

    @staticmethod
    def _validate_withdraw_id(value, field_name, max_length):
        if (
            not isinstance(value, str)
            or not 1 <= len(value) <= max_length
            or not value.isascii()
            or not value.isalnum()
        ):
            raise ValueError("Invalid {}".format(field_name))

        return value
    

    def _submit_withdrawal_once(
        self,
        withdrawal_type,
        request_id,
        payload,
        endpoint,
        signed_params,
        success_validator,
    ):
        """
        Submit withdrawal at most once for a locally reserved ID.

        No automatic retry.
        Ambiguous outcomes require manual reconciliation.
        """
        journal = WithdrawalJournal()

        # Atomic unique-ID reservation.
        # A duplicate raises before any HTTP request.
        journal.reserve(
            withdrawal_type,
            request_id,
            payload,
        )

        # Persist before sending the HTTP request.
        journal.mark_submitting(
            withdrawal_type,
            request_id,
        )

        try:
            signature = self.signer.sign(signed_params)
            headers = self._build_headers(signature)

            response = httpx.post(
                "{}/{}".format(
                    self.base_url,
                    endpoint.lstrip("/"),
                ),
                data=signed_params,
                headers={
                    **headers,
                    "Accept": "application/json",
                    "Content-Type":
                        "application/x-www-form-urlencoded",
                },
                timeout=10.0,
                follow_redirects=False,
            )

            response.raise_for_status()
            result = response.json()

        except Exception:
            journal.mark_result(
                withdrawal_type,
                request_id,
                "UNKNOWN",
            )
            raise

        if not success_validator(result):
            journal.mark_result(
                withdrawal_type,
                request_id,
                "UNKNOWN",
            )
            raise RuntimeError(
                "Ambiguous withdrawal response. "
                "Check withdrawal journal and reconcile "
                "with Indodax before taking further action."
            )

        journal.mark_result(
            withdrawal_type,
            request_id,
            "SUCCESS",
            {
                "confirmed": True,
                "withdrawal_type": withdrawal_type,
            },
        )

        return result

    def withdraw_coin(
        self,
        coin,
        network,
        address,
        amount,
        withdraw_order_id,
        address_tag=None,
        withdraw_method="address",
        withdraw_username=None,
        dry_run=True,
    ):
        import re

        coin = self._validate_coin(coin)

        if not isinstance(network, str):
            raise ValueError("Invalid network")

        network = network.strip()

        if network and not re.fullmatch(r"[A-Za-z0-9]+", network):
            raise ValueError("Invalid network")

        if withdraw_method not in ("address", "username"):
            raise ValueError("Invalid withdrawal method")

        if not isinstance(address, str):
            raise ValueError("Invalid withdrawal address")

        # Documentation marks address as required, including
        # when withdrawMethod=username.
        if not re.fullmatch(r"[A-Za-z0-9:._-]+", address):
            raise ValueError("Invalid withdrawal address")

        amount = self._validate_withdraw_amount(amount)

        withdraw_order_id = self._validate_withdraw_id(
            withdraw_order_id,
            "withdrawOrderId",
            255,
        )

        params = {
            "coin": coin,
            "network": network,
            "address": address,
            "amount": amount,
            "withdrawOrderId": withdraw_order_id,
            "withdrawMethod": withdraw_method,
        }

        if address_tag is not None:
            if not isinstance(address_tag, str):
                raise ValueError("Invalid addressTag")
            params["addressTag"] = address_tag

        if withdraw_method == "username":
            if (
                not isinstance(withdraw_username, str)
                or not re.fullmatch(
                    r"[A-Za-z0-9_-]{4,}",
                    withdraw_username,
                )
            ):
                raise ValueError("Invalid withdrawUsername")

            params["withdrawUsername"] = withdraw_username
        elif withdraw_username is not None:
            raise ValueError(
                "withdrawUsername requires withdrawMethod=username"
            )

        from app.clients.withdrawal_safety import (
            check_crypto_destination,
            check_live_withdrawal_enabled,
        )

        if dry_run:
            return {
                "dry_run": True,
                "request_sent": False,
                "method": "POST",
                "endpoint": "/api/v2/capital/withdraw/apply",
                "params": params,
            }

        check_live_withdrawal_enabled()

        if withdraw_method != "address":
            raise RuntimeError(
                "Live username withdrawal is not enabled yet"
            )

        check_crypto_destination(
            coin=coin,
            network=network,
            address=address,
        )

        
        signed_params = self._build_signed_params(params)

        def crypto_success(result):
            return (
                isinstance(result, dict)
                and isinstance(result.get("id"), str)
                and bool(result["id"])
                and result.get("withdrawOrderId")
                    == withdraw_order_id
            )

        return self._submit_withdrawal_once(
            withdrawal_type="CRYPTO",
            request_id=withdraw_order_id,
            payload=params,
            endpoint="/api/v2/capital/withdraw/apply",
            signed_params=signed_params,
            success_validator=crypto_success,
        )


    def withdraw_idr(
        self,
        amount,
        account_number,
        bank_code,
        client_request_id=None,
        dry_run=True,
    ):
        import re

        if (
            isinstance(amount, bool)
            or not isinstance(amount, int)
            or amount <= 0
        ):
            raise ValueError("IDR withdrawal amount must be a positive integer")
        
        if not 100000 < amount < 1000000000:
            raise ValueError(
                "IDR withdrawal amount must be greater than "
                "100000 and less than 1000000000"
            )

        if (
            not isinstance(account_number, str)
            or not re.fullmatch(r"[0-9]+", account_number)
        ):
            raise ValueError("Invalid bank account number")

        if (
            not isinstance(bank_code, str)
            or not re.fullmatch(r"[0-9]{3}", bank_code)
        ):
            raise ValueError("Bank code must contain exactly 3 digits")

        params = {
            "apiPaymentMethod": "bank_transfer",
            "currency": "IDR",
            "amount": amount,
            "accountInfo": {
                "accountNumber": account_number,
                "bankCodeForPix": bank_code,
            },
        }

        if client_request_id is not None:
            if (
                not isinstance(client_request_id, str)
                or not 1 <= len(client_request_id) <= 36
                or not client_request_id.isascii()
                or not client_request_id.isalnum()
            ):
                raise ValueError("Invalid clientRequestId")

            params["clientRequestId"] = client_request_id

        from app.clients.withdrawal_safety import (
            check_idr_destination,
            check_live_withdrawal_enabled,
        )

        if dry_run:
            return {
                "dry_run": True,
                "request_sent": False,
                "method": "POST",
                "endpoint": "/api/v2/fiat/withdraw",
                "params": params,
            }

        check_live_withdrawal_enabled()

        if not client_request_id:
            raise ValueError(
                "clientRequestId is required for live IDR withdrawal"
            )

        check_idr_destination(
            account_number=account_number,
            bank_code=bank_code,
        )

        form_params = {
            **params,
            "accountInfo": json.dumps(
                params["accountInfo"],
                separators=(",", ":"),
            ),
        }

        
        signed_params = self._build_signed_params(
            form_params
        )

        def idr_success(result):
            if not isinstance(result, dict):
                return False

            data = result.get("data")

            return (
                isinstance(data, dict)
                and isinstance(data.get("orderId"), str)
                and bool(data["orderId"])
            )

        return self._submit_withdrawal_once(
            withdrawal_type="IDR",
            request_id=client_request_id,
            payload=params,
            endpoint="/api/v2/fiat/withdraw",
            signed_params=signed_params,
            success_validator=idr_success,
        )


        response.raise_for_status()
        return response.json()



def create_indodax_client() -> IndodaxClient:
    return IndodaxClient(
        api_key=settings.indodax_api_key,
        secret_key=settings.indodax_secret_key,
        base_url=settings.indodax_base_url,
        recv_window=settings.indodax_recv_window,
    )