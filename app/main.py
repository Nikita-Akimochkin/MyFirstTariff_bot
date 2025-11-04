import os
import asyncio
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)
from aiogram.filters import CommandStart, Command

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Память языка пользователя (пока без БД)
USER_LANG = {}

# Демонстрационные тарифы
TARIFFS = [
    {"code": "T1", "title_ru": "Тариф 1", "title_en": "Plan 1", "price": 10, "days": 7},
    {"code": "T2", "title_ru": "Тариф 2", "title_en": "Plan 2", "price": 25, "days": 30},
    {"code": "T3", "title_ru": "Тариф 3", "title_en": "Plan 3", "price": 70, "days": 90},
]

def tariffs_keyboard(lang: str) -> InlineKeyboardMarkup:
    rows = []
    for t in TARIFFS:
        text = (
            f"{t['title_ru']} — {t['price']} USDT / {t['days']} дней"
            if lang == "ru" else
            f"{t['title_en']} — {t['price']} USDT / {t['days']} days"
        )
        rows.append([InlineKeyboardButton(text=text, callback_data=f"plan:{t['code']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

async def handle_start(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Русский"), KeyboardButton(text="English")]],
        resize_keyboard=True
    )
    await message.answer("Выберите язык / Choose language:", reply_markup=kb)

async def handle_lang(message: Message):
    lang = "ru" if message.text == "Русский" else "en"
    USER_LANG[message.from_user.id] = lang

    title = "Выберите тариф:" if lang == "ru" else "Choose a plan:"
    prompt = "👇 Выберите тариф ниже" if lang == "ru" else "👇 Pick a plan below"

    # 1) убираем клавиатуру выбора языка
    await message.answer(title, reply_markup=ReplyKeyboardRemove())
    # 2) показываем инлайн-кнопки с НЕпустым текстом
    await message.answer(prompt, reply_markup=tariffs_keyboard(lang))


async def handle_ping(message: Message):
    await message.answer("pong 🏓")

async def on_plan_clicked(cb: CallbackQuery):
    _, code = cb.data.split(":", 1)
    lang = USER_LANG.get(cb.from_user.id, "ru")
    t = next((x for x in TARIFFS if x["code"] == code), None)
    if t:
        msg = (
            f"Вы выбрали: {t['title_ru']} — {t['price']} USDT / {t['days']} дней"
            if lang == "ru" else
            f"You chose: {t['title_en']} — {t['price']} USDT / {t['days']} days"
        )
    else:
        msg = "Окей." if lang == "ru" else "OK."
    await cb.answer()
    await cb.message.answer(msg)

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан. Добавь его в .env")
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.message.register(handle_start, CommandStart())
    dp.message.register(handle_ping, Command("ping"))
    dp.message.register(handle_lang, F.text.in_(["Русский", "English"]))
    dp.callback_query.register(on_plan_clicked, F.data.startswith("plan:"))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
