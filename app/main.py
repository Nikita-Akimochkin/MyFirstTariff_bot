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

# Мини-i18n (можно потом вынести в JSON)
I18N = {
    "ru": {
        "start.choose_language": "Выберите язык / Choose language:",
        "tariffs.title": "Выберите тариф:",
        "tariffs.prompt": "👇 Выберите тариф ниже",
        "plan.chosen": "Вы выбрали: {title} — {price} USDT / {days} дней",
        "pong": "pong 🏓",
    },
    "en": {
        "start.choose_language": "Choose your language / Выберите язык:",
        "tariffs.title": "Choose a plan:",
        "tariffs.prompt": "👇 Pick a plan below",
        "plan.chosen": "You chose: {title} — {price} USDT / {days} days",
        "pong": "pong 🏓",
    },
}

def tr(key: str, lang: str = "en", **kwargs) -> str:
    text = I18N.get(lang, I18N["en"]).get(key, key)
    return text.format(**kwargs) if kwargs else text

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
    # Пока язык не выбран — покажем двуязычную подсказку из en-ветки
    await message.answer(tr("start.choose_language", "ru"), reply_markup=kb)

async def handle_lang(message: Message):
    lang = "ru" if message.text == "Русский" else "en"
    USER_LANG[message.from_user.id] = lang
    await message.answer(tr("tariffs.title", lang), reply_markup=ReplyKeyboardRemove())
    await message.answer(tr("tariffs.prompt", lang), reply_markup=tariffs_keyboard(lang))



async def handle_ping(message: Message):
    lang = USER_LANG.get(message.from_user.id, "en")
    await message.answer(tr("pong", lang))


async def on_plan_clicked(cb: CallbackQuery):
    _, code = cb.data.split(":", 1)
    lang = USER_LANG.get(cb.from_user.id, "en")
    t = next((x for x in TARIFFS if x["code"] == code), None)
    msg = tr("plan.chosen", lang, title=(t["title_ru"] if lang=="ru" else t["title_en"]),
             price=t["price"], days=t["days"]) if t else ("Окей." if lang=="ru" else "OK.")
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
