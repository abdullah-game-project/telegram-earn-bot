import logging

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from fastapi import APIRouter, Header, HTTPException, Request, Response

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()

bot_router = APIRouter()

WEBHOOK_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Welcome to the Earn Bot!\n\n"
        f"Your Telegram ID: <code>{message.from_user.id}</code>\n\n"
        "Open the Mini App to start earning.",
        parse_mode="HTML",
    )


@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    await message.answer("💰 Open the Mini App to see your live balance and transaction history.")


@dp.message(Command("id"))
async def cmd_id(message: Message):
    await message.answer(f"Your Telegram ID: <code>{message.from_user.id}</code>", parse_mode="HTML")


@bot_router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None, alias=WEBHOOK_SECRET_HEADER),
):
    if settings.TELEGRAM_WEBHOOK_SECRET and x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot, update)
    except Exception:
        logger.exception("Error handling Telegram webhook update")
        # Still return 200: Telegram retries aggressively on non-2xx, which would
        # just hammer us with the same broken update.
    return Response(status_code=200)
