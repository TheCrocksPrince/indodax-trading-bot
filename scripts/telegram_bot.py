import asyncio
import json
import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from app.clients.binance_client import BinanceClient
from app.clients.indodax_client import IndodaxClient
from app.config.settings import settings
from telegram.constants import ChatType

from decimal import Decimal, InvalidOperation
import re

from app.services.binance_execution_guard import (
    BinanceExecutionGuard,
)

from app.services.telegram_order_journal import (
    TelegramOrderJournal,
)

order_journal = TelegramOrderJournal()

from app.services.telegram_execution_gateway import (
    TelegramExecutionGateway,
)

from app.services.binance_execution_guard import (
    BinanceExecutionGuard,
)

from app.services.dual_exchange_execution import DualExchangeExecution

from app.services.live_telegram_execution import LiveTelegramExecution


load_dotenv()

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ALLOWED_USER_ID = os.getenv(
    "TELEGRAM_ALLOWED_USER_ID", ""
).strip()


def get_client(exchange):
    exchange = exchange.lower()

    if exchange == "binance":
        return BinanceClient(read_only=True)

    if exchange == "indodax":
        return IndodaxClient(
            api_key=settings.indodax_api_key,
            secret_key=settings.indodax_secret_key,
            base_url=settings.indodax_base_url,
            recv_window=settings.indodax_recv_window,
        )

    raise ValueError(
        "Exchange harus binance atau indodax"
    )


async def authorized(update):
    user = update.effective_user
    chat = update.effective_chat

    if (
        user is None
        or chat is None
        or chat.type != ChatType.PRIVATE
        or str(user.id) != ALLOWED_USER_ID
    ):
        if update.effective_message:
            await update.effective_message.reply_text(
                "Unauthorized."
            )
        return False

    return True


async def send_result(update, result):
    output = json.dumps(
        result,
        indent=2,
        default=str,
    )

    # Keep Telegram messages within a safe size.
    if len(output) > 3500:
        output = output[:3500] + "\n...truncated"

    await update.effective_message.reply_text(output)


async def start(update, context):
    if not await authorized(update):
        return

    await update.message.reply_text(
        "Trading Bot connected.\n\n"
        "Available commands:\n"
        "/status\n"
        "/balance binance\n"
        "/balance indodax\n"
        "/orders binance\n"
        "/orders indodax\n"
        "/buy EXCHANGE SYMBOL QUANTITY PRICE\n"
        "/sell EXCHANGE SYMBOL QUANTITY PRICE\n\n"
        "Mode: Production Read-Only + Order Preview"
    )


async def status(update, context):
    if not await authorized(update):
        return

    await update.message.reply_text(
        "Telegram: CONNECTED\n"
        "Binance: Production Read-Only\n"
        "Indodax: Production Read-Only via Telegram\n"
        "Order execution: DISABLED"
    )


async def balance(update, context):
    if not await authorized(update):
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage: /balance binance|indodax"
        )
        return

    exchange = context.args[0].lower()

    try:
        client = get_client(exchange)

        result = await asyncio.to_thread(
            client.get_account
        )

        await send_result(update, result)

    except Exception as exc:
        logging.exception("Balance request failed")
        await update.message.reply_text(
            "Balance request failed: "
            + type(exc).__name__
        )


async def orders(update, context):
    if not await authorized(update):
        return

    if len(context.args) not in (1, 2):
        await update.message.reply_text(
            "Usage: /orders binance|indodax [SYMBOL]"
        )
        return

    exchange = context.args[0].lower()
    symbol = (
        context.args[1].upper()
        if len(context.args) == 2
        else None
    )

    try:
        client = get_client(exchange)

        if symbol:
            result = await asyncio.to_thread(
                client.get_open_orders,
                symbol,
            )
        else:
            result = await asyncio.to_thread(
                client.get_open_orders
            )

        await send_result(update, result)

    except Exception as exc:
        logging.exception("Orders request failed")
        await update.message.reply_text(
            "Orders request failed: "
            + type(exc).__name__
        )

async def preview_order(update, context, side):
    if not await authorized(update):
        return

    if len(context.args) != 4:
        await update.message.reply_text(
            f"Usage: /{side.lower()} "
            "binance|indodax SYMBOL QUANTITY PRICE"
        )
        return

    exchange, symbol, quantity_raw, price_raw = context.args
    exchange = exchange.lower()
    symbol = symbol.upper()

    if exchange not in {"binance", "indodax"}:
        await update.message.reply_text(
            "Exchange harus binance atau indodax."
        )
        return

    if not re.fullmatch(r"[A-Z0-9]+", symbol):
        await update.message.reply_text(
            "Invalid symbol."
        )
        return

    try:
        quantity = Decimal(quantity_raw)
        price = Decimal(price_raw)

        if (
            not quantity.is_finite()
            or not price.is_finite()
            or quantity <= 0
            or price <= 0
        ):
            raise ValueError("Invalid quantity or price")

        if exchange == "binance":
            guard = BinanceExecutionGuard()
            validated = guard.validate(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
            )
            notional = Decimal(
                validated["notional_usdt"]
            )
            quote_currency = "USDT"
        else:
            if not symbol.endswith("IDR"):
                raise ValueError(
                    "Preview Indodax sementara hanya mendukung pair IDR"
                )

            notional = quantity * price
            quote_currency = "IDR"

    except (InvalidOperation, ValueError, PermissionError) as exc:
        await update.message.reply_text(
            f"Order rejected: {exc}"
        )
        return
    
    intent_id = await asyncio.to_thread(
        order_journal.create_intent,
        update.effective_user.id,
        exchange,
        symbol,
        side,
        quantity,
        price,
    )

    await update.message.reply_text(
        "ORDER PREVIEW — NOT SUBMITTED\n\n"
        f"Exchange: {exchange.upper()}\n"
        f"Side: {side}\n"
        f"Symbol: {symbol}\n"
        f"Quantity: {quantity}\n"
        f"Limit Price: {price}\n"
        f"Estimated Notional: {notional} {quote_currency}\n\n"
        f"Preview ID: {intent_id}\n\n"
        f"Confirm with:\n/confirm {intent_id}\n\n"
        "Expires in 2 minutes.\n"
        "Confirmation will NOT submit an exchange order."
    )


async def buy(update, context):
    await preview_order(update, context, "BUY")


async def sell(update, context):
    await preview_order(update, context, "SELL")

async def confirm(update, context):
    if not await authorized(update):
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage: /confirm INTENT_ID"
        )
        return

    intent_id = context.args[0]

    try:
        result = await asyncio.to_thread(
            order_journal.confirm_intent,
            intent_id,
            update.effective_user.id,
        )

        await update.message.reply_text(
            "PREVIEW CONFIRMED\n\n"
            f"Exchange: {result['exchange']}\n"
            f"Symbol: {result['symbol']}\n"
            f"Side: {result['side']}\n"
            f"Quantity: {result['quantity']}\n"
            f"Price: {result['price']}\n\n"
            "No production order submitted."
        )

    except ValueError as exc:
        await update.message.reply_text(str(exc))

async def prepare(update, context):
    if not await authorized(update):
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage: /prepare INTENT_ID"
        )
        return

    try:
        gateway = TelegramExecutionGateway()

        result = await asyncio.to_thread(
            gateway.prepare_binance,
            context.args[0],
            update.effective_user.id,
        )

        await send_result(update, result)

    except (ValueError, PermissionError) as exc:
        logging.warning(
            "Order preparation rejected: %s",
            type(exc).__name__,
        )

        await update.message.reply_text(
            f"Preparation rejected: {exc}"
        )

    except Exception:
        logging.exception("Order preparation failed")

        await update.message.reply_text(
            "Preparation failed. Check server logs."
        )

async def execution_status(update, context):
    if not await authorized(update):
        return

    guard = BinanceExecutionGuard()

    await update.message.reply_text(
        "PRODUCTION EXECUTION STATUS\n\n"
        f"Binance live flag: {'ON' if guard.enabled else 'OFF'}\n"
        f"Binance max notional: {guard.max_notional} USDT\n"
        "Binance transport: LOCKED\n"
        "Indodax Telegram execution: NOT INTEGRATED\n"
        "Live authorization: NOT IMPLEMENTED\n"
        "Order reconciliation: NOT COMPLETE\n\n"
        "Production execution: NOT READY"
    )

async def preflight(update, context):
    if not await authorized(update):
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage: /preflight INTENT_ID"
        )
        return

    try:
        result = await asyncio.to_thread(
            DualExchangeExecution().prepare,
            context.args[0],
            update.effective_user.id,
        )

        await send_result(update, result)

    except Exception as exc:
        logging.exception("Preflight failed")
        await update.message.reply_text(
            f"Preflight rejected: {type(exc).__name__}"
        )

async def live_create(update, context):
    if not await authorized(update):
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage: /live_create INTENT_ID"
        )
        return

    try:
        result = await asyncio.to_thread(
            LiveTelegramExecution().stage_create,
            context.args[0],
            update.effective_user.id,
        )
        await send_result(update, result)

    except Exception as exc:
        logging.exception("Live create staging failed")
        await update.message.reply_text(
            f"Rejected: {type(exc).__name__}: {exc}"
        )


async def live_cancel(update, context):
    if not await authorized(update):
        return

    if len(context.args) != 3:
        await update.message.reply_text(
            "Usage: /live_cancel EXCHANGE SYMBOL ORDER_ID"
        )
        return

    try:
        result = await asyncio.to_thread(
            LiveTelegramExecution().stage_cancel,
            *context.args,
            update.effective_user.id,
        )
        await send_result(update, result)

    except Exception as exc:
        logging.exception("Live cancel staging failed")
        await update.message.reply_text(
            f"Rejected: {type(exc).__name__}: {exc}"
        )


async def live_confirm(update, context):
    if not await authorized(update):
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage: /live_confirm ACTION_ID"
        )
        return

    try:
        result = await asyncio.to_thread(
            LiveTelegramExecution().execute,
            context.args[0],
            update.effective_user.id,
        )
        await send_result(update, result)

    except Exception as exc:
        logging.exception("Live execution failed")
        await update.message.reply_text(
            f"Execution error: {type(exc).__name__}. "
            "Outcome may be UNKNOWN. "
            "Check exchange order history before retrying."
        )

async def live_status(update, context):
    if not await authorized(update):
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage: /live_status ACTION_ID"
        )
        return

    try:
        result = await asyncio.to_thread(
            LiveTelegramExecution().get_action_status,
            context.args[0],
            update.effective_user.id
        )
        await send_result(update, result)

    except Exception as exc:
        logging.exception("Live status failed")
        await update.message.reply_text(
            f"Status unavailable: {type(exc).__name__}"
        )

def main():
    if not TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing"
        )

    if not ALLOWED_USER_ID.isdigit():
        raise RuntimeError(
            "TELEGRAM_ALLOWED_USER_ID is invalid"
        )

    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )
    application.add_handler(
        CommandHandler("status", status)
    )
    application.add_handler(
        CommandHandler("balance", balance)
    )
    application.add_handler(
        CommandHandler("orders", orders)
    )
    application.add_handler(
        CommandHandler("buy", buy)
    )
    application.add_handler(
        CommandHandler("sell", sell)
    )
    application.add_handler(
        CommandHandler("confirm", confirm)
    )
    application.add_handler(
        CommandHandler("prepare", prepare)
    )
    application.add_handler(
        CommandHandler(
            "execution_status",
            execution_status,
        )
    )
    application.add_handler(
        CommandHandler("preflight", preflight)
    )
    application.add_handler(
        CommandHandler("live_create", live_create)
    )

    application.add_handler(
        CommandHandler("live_cancel", live_cancel)
    )

    application.add_handler(
        CommandHandler("live_confirm", live_confirm)
    )
    application.add_handler(
        CommandHandler("live_status", live_status)
    )

    print("Telegram Trading Bot starting...")
    print("Production execution: DISABLED")

    application.run_polling()




if __name__ == "__main__":
    main()