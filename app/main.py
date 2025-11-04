import os
import asyncio
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message, CallbackQuery, BotCommand,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)
from aiogram.filters import CommandStart, Command

# =========================
# 1) Окружение / конфиг
# =========================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")


# =========================
# 2) mini-i18n
# =========================
I18N = {
    "ru": {
        "start.choose_language": "Выберите язык / Choose language:",
        "menu.title": "Главное меню",
        "menu.btn.tariffs": "📋 Тарифы",
        "menu.btn.lang": "🌐 Язык",
        "menu.btn.help": "ℹ️ Помощь",
        "help.text": "Доступные команды:\n/start — начать\n/menu — меню\n/lang — сменить язык\n/ping — проверка связи",
        "tariffs.title": "Выберите тариф:",
        "tariffs.prompt": "👇 Выберите тариф ниже",
        "plan.chosen": "Вы выбрали: {title} — {price} USDT / {days} дней",
        "pong": "pong 🏓",
        "pay.instructions": "💸 Отправьте оплату на один из адресов ниже:",
        "pay.send_proof_button": "Отправить хэш / скрин",
        "pay.soon": "Скоро добавим приём хэша/скрина и отправку админу 🙌",
    },
    "en": {
        "start.choose_language": "Choose your language / Выберите язык:",
        "menu.title": "Main menu",
        "menu.btn.tariffs": "📋 Plans",
        "menu.btn.lang": "🌐 Language",
        "menu.btn.help": "ℹ️ Help",
        "help.text": "Available commands:\n/start — start\n/menu — menu\n/lang — change language\n/ping — connectivity check",
        "tariffs.title": "Choose a plan:",
        "tariffs.prompt": "👇 Pick a plan below",
        "plan.chosen": "You chose: {title} — {price} USDT / {days} days",
        "pong": "pong 🏓",
        "pay.instructions": "💸 Send payment to one of the addresses below:",
        "pay.send_proof_button": "Send TX hash / screenshot",
        "pay.soon": "We’ll add proof submission and admin notify soon 🙌",
    },
}
def tr(key: str, lang: str = "en", **kwargs) -> str:
    text = I18N.get(lang, I18N["en"]).get(key, key)
    return text.format(**kwargs) if kwargs else text


# =========================
# 3) Runtime-память (до БД)
# =========================
USER_LANG: dict[int, str] = {}


# =========================
# 4) Статика (демо)
# =========================
TARIFFS = [
    {"code": "T1", "title_ru": "Тариф 1", "title_en": "Plan 1", "price": 10, "days": 7},
    {"code": "T2", "title_ru": "Тариф 2", "title_en": "Plan 2", "price": 25, "days": 30},
    {"code": "T3", "title_ru": "Тариф 3", "title_en": "Plan 3", "price": 70, "days": 90},
]
WALLETS = [
    {"label": "USDT TRC20", "address": "TXXXXXXXXXXXX"},
    {"label": "BTC",        "address": "bc1qXXXXXXXXX"},
]


# =========================
# 5) Клавиатуры
# =========================
def tariffs_keyboard(lang: str) -> InlineKeyboardMarkup:
    rows = []
    for t in TARIFFS:
        text = (
            f"{t['title_ru']} — {t['price']} USDT / {t['days']} дней"
            if lang == "ru"
            else f"{t['title_en']} — {t['price']} USDT / {t['days']} days"
        )
        rows.append([InlineKeyboardButton(text=text, callback_data=f"plan:{t['code']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def payment_keyboard(lang: str, code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=tr("pay.send_proof_button", lang), callback_data=f"proof:{code}")]]
    )

def main_menu_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=tr("menu.btn.tariffs", lang))],
            [KeyboardButton(text=tr("menu.btn.lang", lang)), KeyboardButton(text=tr("menu.btn.help", lang))],
        ],
        resize_keyboard=True
    )


# =========================
# 6) Helpers
# =========================
def payment_instructions_text(lang: str) -> str:
    lines = [tr("pay.instructions", lang)]
    for w in WALLETS:
        lines.append(f"{w['label']}: {w['address']}")
    return "\n".join(lines)


# =========================
# 7) Handlers
# =========================
async def handle_start(message: Message):
    # Показ выбора языка (меню добавим после выбора)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Русский"), KeyboardButton(text="English")]],
        resize_keyboard=True
    )
    await message.answer(tr("start.choose_language", "en"), reply_markup=kb)

async def handle_lang(message: Message):
    # Выбор языка + включаем постоянное меню и показываем тарифы
    lang = "ru" if message.text == "Русский" else "en"
    USER_LANG[message.from_user.id] = lang

    await message.answer(tr("menu.title", lang), reply_markup=main_menu_kb(lang))
    await message.answer(tr("tariffs.title", lang))
    await message.answer(tr("tariffs.prompt", lang), reply_markup=tariffs_keyboard(lang))

async def handle_menu_cmd(message: Message):
    lang = USER_LANG.get(message.from_user.id, "en")
    await message.answer(tr("menu.title", lang), reply_markup=main_menu_kb(lang))

async def handle_lang_cmd(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Русский"), KeyboardButton(text="English")]],
        resize_keyboard=True
    )
    await message.answer(tr("start.choose_language", "en"), reply_markup=kb)

async def handle_help_cmd(message: Message):
    lang = USER_LANG.get(message.from_user.id, "en")
    await message.answer(tr("help.text", lang))

async def handle_ping(message: Message):
    lang = USER_LANG.get(message.from_user.id, "en")
    await message.answer(tr("pong", lang))

async def handle_menu_buttons(message: Message):
    # Обрабатываем текстовые кнопки меню (RU/EN)
    text = message.text
    lang = USER_LANG.get(message.from_user.id, "en")
    if text in ("📋 Тарифы", "📋 Plans"):
        await message.answer(tr("tariffs.title", lang))
        await message.answer(tr("tariffs.prompt", lang), reply_markup=tariffs_keyboard(lang))
    elif text in ("🌐 Язык", "🌐 Language"):
        await handle_lang_cmd(message)
    elif text in ("ℹ️ Помощь", "ℹ️ Help"):
        await handle_help_cmd(message)

async def on_plan_clicked(cb: CallbackQuery):
    _, code = cb.data.split(":", 1)
    lang = USER_LANG.get(cb.from_user.id, "en")
    # Сообщим, какой тариф выбран
    t = next((x for x in TARIFFS if x["code"] == code), None)
    if t:
        await cb.message.answer(tr("plan.chosen", lang,
                                   title=t["title_ru"] if lang == "ru" else t["title_en"],
                                   price=t["price"], days=t["days"]))
    await cb.answer()
    # Показ реквизитов и кнопки отправки пруфа
    await cb.message.answer(payment_instructions_text(lang), reply_markup=payment_keyboard(lang, code))

async def on_proof_clicked(cb: CallbackQuery):
    lang = USER_LANG.get(cb.from_user.id, "en")
    await cb.answer()
    await cb.message.answer(tr("pay.soon", lang))


# =========================
# 8) main() / entry
# =========================
async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан. Добавь его в .env")

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Системное меню команд (кнопка ≡ в Telegram)
    await bot.set_my_commands([
        BotCommand(command="menu", description="Меню / Menu"),
        BotCommand(command="lang", description="Сменить язык / Change language"),
        BotCommand(command="ping", description="Проверка связи / Ping"),
        BotCommand(command="help", description="Помощь / Help"),
    ])

    # Регистрация хендлеров — специфичные раньше
    dp.message.register(handle_start, CommandStart())
    dp.message.register(handle_ping, Command("ping"))
    dp.message.register(handle_menu_cmd, Command("menu"))
    dp.message.register(handle_lang_cmd, Command("lang"))
    dp.message.register(handle_help_cmd, Command("help"))

    dp.callback_query.register(on_plan_clicked, F.data.startswith("plan:"))
    dp.callback_query.register(on_proof_clicked, F.data.startswith("proof:"))

    dp.message.register(handle_lang, F.text.in_(["Русский", "English"]))  # выбор языка
    dp.message.register(handle_menu_buttons, F.text.in_([
        "📋 Тарифы", "📋 Plans",
        "🌐 Язык", "🌐 Language",
        "ℹ️ Помощь", "ℹ️ Help",
    ]))

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
