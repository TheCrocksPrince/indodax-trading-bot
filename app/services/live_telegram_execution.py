import hashlib
import hmac
import json
import os
import re
import sqlite3
import time
import uuid

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode

import httpx

from app.clients.binance_client import BinanceClient
from app.clients.binance_execution_client import BinanceExecutionClient
from app.clients.indodax_client import create_indodax_client
from app.services.telegram_order_journal import TelegramOrderJournal

from app.services.indodax_live_validation import (
    get_pair_rules,
    validate_market_rules,
    validate_available_balance,
    validate_order_response,
    validate_cancel_response,
)

class LiveTelegramExecution:
    def __init__(self, path="data/live_telegram_execution.db"):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)

        with self._db() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    action_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    exchange TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT,
                    quantity TEXT,
                    price TEXT,
                    target_order_id TEXT,
                    status TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    result TEXT,
                    created_at TEXT NOT NULL
                )
            """)

    def _db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        return db

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _enabled(exchange):
        key = (
            "BINANCE_ENABLE_LIVE_TRADING"
            if exchange == "binance"
            else "INDODAX_ENABLE_LIVE_TRADING"
        )
        if os.getenv(key, "false").lower() != "true":
            raise PermissionError("Live trading disabled: " + key)

    @staticmethod
    def _limit(exchange, quantity, price):
        q = Decimal(str(quantity))
        p = Decimal(str(price))

        if not (q.is_finite() and p.is_finite() and q > 0 and p > 0):
            raise ValueError("Invalid order numbers")

        key = (
            "BINANCE_MAX_ORDER_NOTIONAL_USDT"
            if exchange == "binance"
            else "INDODAX_MAX_ORDER_NOTIONAL_IDR"
        )

        cap = Decimal(
            os.getenv(
                key,
                "10" if exchange == "binance" else "100000"
            )
        )

        if not cap.is_finite() or cap <= 0 or q * p > cap:
            raise PermissionError("Notional exceeds limit")

        return str(q * p)

    def _insert(
        self, action_id, user_id, exchange, operation,
        symbol, side=None, quantity=None, price=None,
        target_order_id=None
    ):
        now = datetime.now(timezone.utc)

        try:
            with self._db() as db:
                db.execute("""
                    INSERT INTO actions (
                        action_id, user_id, exchange, operation,
                        symbol, side, quantity, price,
                        target_order_id, status, expires_at, created_at
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        'AWAITING_LIVE_CONFIRM', ?, ?
                    )
                """, (
                    action_id, user_id, exchange, operation,
                    symbol, side, quantity, price, target_order_id,
                    (now + timedelta(seconds=60)).isoformat(),
                    now.isoformat()
                ))
        except sqlite3.IntegrityError as exc:
            raise PermissionError(
                "Action already exists. Duplicate execution blocked."
            ) from exc

    def stage_create(self, intent_id, user_id):
        with TelegramOrderJournal()._connect() as db:
            row = db.execute("""
                SELECT exchange, symbol, side, quantity,
                    price, status, expires_at
                FROM telegram_order_intents
                WHERE intent_id=? AND user_id=?
            """, (intent_id, user_id)).fetchone()

        if row is None:
            raise PermissionError("Unknown intent or owner")

        exchange, symbol, side, qty, price, status, expiry = row

        if exchange not in ("binance", "indodax"):
            raise ValueError("Unsupported exchange")

        if status != "CONFIRMED_PREVIEW":
            raise PermissionError("Confirmed preview required")

        if datetime.fromisoformat(expiry) <= datetime.now(timezone.utc):
            raise PermissionError("Preview expired")

        # Check maximum notional configured in .env
        notional = self._limit(exchange, qty, price)

        if exchange == "binance":
            BinanceExecutionClient().prepare_limit_order(
                symbol, side, qty, price
            )

        else:
            # INDODAX VALIDATION
            if not symbol.endswith("IDR"):
                raise ValueError("Only IDR pairs supported")

            order = {
                "symbol": symbol,
                "side": side,
                "quantity": qty,
                "price": price,
            }

            # 1. Fetch trading rules
            rules = get_pair_rules(symbol)

            # 2. Validate minimum quantity, notional, increments
            market_check = validate_market_rules(order, rules)

            # 3. Fetch account balances
            indodax_client = create_indodax_client()
            account = indodax_client.get_account()

            # 4. Check available balance
            balance_check = validate_available_balance(
                account,
                order,
                rules,
            )

            # 5. Apply 1% balance buffer for BUY
            if side == "BUY":
                required_with_buffer = (
                    Decimal(market_check["notional_idr"])
                    * Decimal("1.01")
                )

                if (
                    Decimal(balance_check["available"])
                    < required_with_buffer
                ):
                    raise PermissionError(
                        "Insufficient IDR balance including safety buffer"
                    )

            # 6. Dry-run order (no production submission)
            check = indodax_client.create_order(
                symbol=symbol,
                side=side,
                quantity=qty,
                price=price,
                order_type="LIMIT",
                time_in_force="GTC",
                dry_run=True,
            )

            if check.get("sent") is not False:
                raise RuntimeError("Dry-run verification failed")

        # Prevent duplicate staging
        with self._db() as db:
            existing = db.execute(
                """
                SELECT status
                FROM actions
                WHERE action_id=?
                """,
                (intent_id,)
            ).fetchone()

        if existing is not None:
            raise PermissionError(
                "Intent already staged or executed"
            )

        # Store action awaiting explicit live confirmation
        self._insert(
            intent_id,
            user_id,
            exchange,
            "CREATE",
            symbol,
            side,
            qty,
            price,
        )

        return {
            "action_id": intent_id,
            "exchange": exchange,
            "side": side,
            "symbol": symbol,
            "quantity": qty,
            "price": price,
            "notional": notional,
            "status": "AWAITING_LIVE_CONFIRM",
            "confirm": "/live_confirm " + intent_id,
        }

    def stage_cancel(self, exchange, symbol, order_id, user_id):
        exchange = exchange.lower()
        symbol = symbol.upper()
        order_id = str(order_id)

        if exchange not in ("binance", "indodax"):
            raise ValueError("Unsupported exchange")

        if not re.fullmatch(r"[A-Z0-9]+", symbol):
            raise ValueError("Invalid symbol")

        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", order_id):
            raise ValueError("Invalid order ID")

        # Cancellation restricted to acknowledged bot-created orders.
        with self._db() as db:
            rows = db.execute("""
                SELECT result
                FROM actions
                WHERE exchange=?
                  AND symbol=?
                  AND operation='CREATE'
                  AND status='ACKNOWLEDGED'
                  AND user_id=?
            """, (exchange, symbol, user_id)).fetchall()

        owned = False

        for row in rows:
            try:
                result = json.loads(row["result"])
                if str(result.get("orderId", "")) == order_id:
                    owned = True
                    break
            except (TypeError, ValueError):
                continue

        if not owned:
            raise PermissionError(
                "Order not found in bot-owned acknowledged orders"
            )

        action_id = uuid.uuid4().hex

        self._insert(
            action_id,
            user_id,
            exchange,
            "CANCEL",
            symbol,
            target_order_id=order_id
        )

        return {
            "action_id": action_id,
            "exchange": exchange,
            "symbol": symbol,
            "order_id": order_id,
            "status": "AWAITING_LIVE_CONFIRM",
            "confirm": "/live_confirm " + action_id
        }

    def _binance_request(self, method, params):
        client = BinanceClient(read_only=True)

        if not client.api_key or not client.secret_key:
            raise RuntimeError("Missing Binance credentials")

        params = dict(params)
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = 5000

        payload = urlencode(params)

        params["signature"] = hmac.new(
            client.secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "X-MBX-APIKEY": client.api_key,
            "Accept": "application/json"
        }

        with httpx.Client(
            timeout=10,
            follow_redirects=False,
            trust_env=False
        ) as http:
            request_kwargs = {
                "headers": headers,
            }

            if method == "POST":
                request_kwargs["data"] = params
            elif method == "DELETE":
                request_kwargs["params"] = params
            else:
                raise ValueError("Unsupported HTTP method")

            response = http.request(
                method,
                client.base_url + "/api/v3/order",
                **request_kwargs
            )
            response.raise_for_status()
            return response.json()

    def execute(self, action_id, user_id):
        # Claim once before any outbound request.
        with self._db() as db:
            cursor = db.execute("""
                UPDATE actions
                SET status='SUBMITTING'
                WHERE action_id=?
                  AND user_id=?
                  AND status='AWAITING_LIVE_CONFIRM'
                  AND expires_at>?
            """, (action_id, user_id, self._now()))

            if cursor.rowcount != 1:
                raise PermissionError(
                    "Action expired, already claimed, or unauthorized"
                )

            row = dict(db.execute(
                "SELECT * FROM actions WHERE action_id=?",
                (action_id,)
            ).fetchone())

        exchange = row["exchange"]
        operation = row["operation"]
        symbol = row["symbol"]

        try:
            self._enabled(exchange)

            if operation == "CREATE":
                self._limit(
                    exchange, row["quantity"], row["price"]
                )

                if exchange == "binance":
                    BinanceExecutionClient().prepare_limit_order(
                        symbol,
                        row["side"],
                        row["quantity"],
                        row["price"]
                    )

                    result = self._binance_request(
                        "POST",
                        {
                            "symbol": symbol,
                            "side": row["side"],
                            "type": "LIMIT",
                            "timeInForce": "GTC",
                            "quantity": row["quantity"],
                            "price": row["price"],
                            "newClientOrderId": "bot_" + action_id[:24]
                        }
                    )
                else:
                    result = create_indodax_client().create_order(
                        symbol=symbol,
                        side=row["side"],
                        quantity=row["quantity"],
                        price=row["price"],
                        dry_run=False
                    )

            elif operation == "CANCEL":
                order_id = row["target_order_id"]

                if exchange == "binance":
                    if not order_id.isdigit():
                        raise ValueError("Invalid Binance order ID")

                    result = self._binance_request(
                        "DELETE",
                        {
                            "symbol": symbol,
                            "orderId": order_id
                        }
                    )
                else:
                    result = create_indodax_client().cancel_order(
                        symbol=symbol,
                        order_id=int(order_id),
                        dry_run=False
                    )
            else:
                raise ValueError("Unsupported operation")

            if not isinstance(result, dict):
                raise RuntimeError("Unexpected exchange response")

            if result.get("orderId") is None:
                raise RuntimeError("Missing exchange order ID")

            if operation == "CREATE" and exchange == "binance":
                expected = "bot_" + action_id[:24]

                if (
                    result.get("clientOrderId") != expected
                    or result.get("symbol") != symbol
                ):
                    raise RuntimeError(
                        "Binance response identity mismatch"
                    )

            with self._db() as db:
                db.execute("""
                    UPDATE actions
                    SET status='ACKNOWLEDGED', result=?
                    WHERE action_id=?
                """, (
                    json.dumps(result, default=str),
                    action_id
                ))

            return {
                "action_id": action_id,
                "exchange": exchange,
                "operation": operation,
                "status": "ACKNOWLEDGED",
                "exchange_response": result
            }

        except Exception:
            # Never automatically retry an uncertain order.
            with self._db() as db:
                db.execute("""
                    UPDATE actions
                    SET status='UNKNOWN'
                    WHERE action_id=?
                      AND status='SUBMITTING'
                """, (action_id,))
            raise

    def get_action_status(self, action_id, user_id):
        with self._db() as db:
            row = db.execute(
                """
                SELECT action_id, exchange, operation,
                    symbol, status, target_order_id,
                    result, created_at
                FROM actions
                WHERE action_id=? AND user_id=?
                """,
                (action_id, user_id)
            ).fetchone()

        if row is None:
            raise PermissionError("Action not found")

        result = dict(row)

        if result["result"]:
            result["result"] = json.loads(result["result"])

        return result