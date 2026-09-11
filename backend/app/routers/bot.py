from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from fastapi import APIRouter, Request, Response
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()

bot_router = APIRouter()   # renamed to avoid confusion

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"👋 Welcome to the Earn Bot!\n\n"
        f"Your Telegram ID: <code>{message.from_user.id}</code>\n\n"
        f"Open the Mini App to start earning.",
        parse_mode="HTML"
    )

@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    await message.answer("💰 Balance feature coming soon. Open the Mini App for full details.")

@dp.message(Command("id"))
async def cmd_id(message: Message):
    await message.answer(
        f"Your Telegram ID: <code>{message.from_user.id}</code>",
        parse_mode="HTML"
    )

@bot_router.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return Response(status_code=200)
