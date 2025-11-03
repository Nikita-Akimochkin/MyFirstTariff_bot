import os
import asyncio
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties  # <-- новый импорт
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

load_dotenv()  # подтянет BOT_TOKEN из .env
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def handle_start(message: Message):
    await message.answer("👋 Бот запущен. Готов к работе!\nНапиши /ping для проверки отклика.")

async def handle_ping(message: Message):
    await message.answer("pong 🏓")

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан. Добавь его в .env")
    # aiogram 3.7+: parse_mode задаём через default=DefaultBotProperties(...)
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.message.register(handle_start, CommandStart())
    dp.message.register(handle_ping, Command("ping"))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
