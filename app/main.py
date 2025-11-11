# app/main.py
import os
import time
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

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
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ========== config / env ==========
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHANNEL_ID = os.getenv("ADMIN_CHANNEL_ID")  # MUST be set
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")  # optional

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in .env")
if not ADMIN_CHANNEL_ID:
    raise RuntimeError("ADMIN_CHANNEL_ID is not set in .env (admin log channel id)")

ADMIN_CHANNEL_ID_INT = int(ADMIN_CHANNEL_ID)

# ========== storage helper ==========
DATA_DIR = Path("data")
PAYMENTS_FILE = DATA_DIR / "payments.json"
DATA_DIR.mkdir(exist_ok=True)

def load_payments() -> Dict[str, Any]:
    if not PAYMENTS_FILE.exists():
        return {}
    with PAYMENTS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_payments(d: Dict[str, Any]) -> None:
    with PAYMENTS_FILE.open("w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

# ensure file exists
if not PAYMENTS_FILE.exists():
    save_payments({})

# ========== mini-i18n ==========
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
        "proof.received": "Заявка принята, ожидайте подтверждения.",
        "admin.new_payment": "💰 Новый запрос на оплату!\n👤 Username: {uname}\n💳 Тариф: {tline}\n{hash_line}",
        "admin.paid_btn": "Оплачено ✅",
        "admin.rej_btn": "Отклонить ❌",
        "user.paid_confirmed": "✅ Оплата подтверждена! {invite_text}",
        "user.rejected": "❌ Оплата отклонена. Если это ошибка — свяжитесь с поддержкой.",
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
        "proof.received": "Submitted, please wait for confirmation.",
        "admin.new_payment": "💰 New payment request!\n👤 Username: {uname}\n💳 Plan: {tline}\n{hash_line}",
        "admin.paid_btn": "Paid ✅",
        "admin.rej_btn": "Reject ❌",
        "user.paid_confirmed": "✅ Payment confirmed! {invite_text}",
        "user.rejected": "❌ Payment was rejected. If this is a mistake, contact support.",
    }
}
def tr(key: str, lang: str = "en", **kwargs) -> str:
    text = I18N.get(lang, I18N["en"]).get(key, key)
    return text.format(**kwargs) if kwargs else text

# ========== runtime memory ==========
USER_LANG: Dict[int, str] = {}

# demo tariffs & wallets
TARIFFS = [
    {"code": "T1", "title_ru": "Тариф 1", "title_en": "Plan 1", "price": 10, "days": 7},
    {"code": "T2", "title_ru": "Тариф 2", "title_en": "Plan 2", "price": 25, "days": 30},
    {"code": "T3", "title_ru": "Тариф 3", "title_en": "Plan 3", "price": 70, "days": 90},
]
WALLETS = [
    {"label": "USDT TRC20", "address": "TXXXXXXXXXXXX"},
    {"label": "BTC", "address": "bc1qXXXXXXXXX"},
]

# ========== fsm ==========
class ProofStates(StatesGroup):
    waiting_for_proof = State()

# ========== keyboards ==========
def tariffs_keyboard(lang: str) -> InlineKeyboardMarkup:
    rows = []
    for t in TARIFFS:
        text = (f"{t['title_ru']} — {t['price']} USDT / {t['days']} дней" if lang == "ru"
                else f"{t['title_en']} — {t['price']} USDT / {t['days']} days")
        rows.append([InlineKeyboardButton(text=text, callback_data=f"plan:{t['code']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def payment_keyboard(lang: str, code: str) -> InlineKeyboardMarkup:
    text = tr("pay.send_proof_button", lang)
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=f"proof:{code}")]])

def main_menu_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=tr("menu.btn.tariffs", lang))],
            [KeyboardButton(text=tr("menu.btn.lang", lang)), KeyboardButton(text=tr("menu.btn.help", lang))],
        ],
        resize_keyboard=True
    )

def payment_instructions_text(lang: str) -> str:
    lines = [tr("pay.instructions", lang)]
    for w in WALLETS:
        lines.append(f"{w['label']}: {w['address']}")
    return "\n".join(lines)

# ========== bot handlers ==========
async def handle_start(message: Message):
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Русский"), KeyboardButton(text="English")]], resize_keyboard=True)
    await message.answer(tr("start.choose_language", "en"), reply_markup=kb)

async def handle_lang(message: Message, state: FSMContext):
    lang = "ru" if message.text == "Русский" else "en"
    USER_LANG[message.from_user.id] = lang
    # show main menu and tariffs
    await message.answer(tr("menu.title", lang), reply_markup=main_menu_kb(lang))
    await message.answer(tr("tariffs.title", lang))
    await message.answer(tr("tariffs.prompt", lang), reply_markup=tariffs_keyboard(lang))

async def handle_menu_cmd(message: Message):
    lang = USER_LANG.get(message.from_user.id, "en")
    await message.answer(tr("menu.title", lang), reply_markup=main_menu_kb(lang))

async def handle_lang_cmd(message: Message):
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Русский"), KeyboardButton(text="English")]], resize_keyboard=True)
    await message.answer(tr("start.choose_language", "en"), reply_markup=kb)

async def handle_help_cmd(message: Message):
    lang = USER_LANG.get(message.from_user.id, "en")
    await message.answer(tr("help.text", lang))

async def handle_ping(message: Message):
    lang = USER_LANG.get(message.from_user.id, "en")
    await message.answer(tr("pong", lang))

async def handle_menu_buttons(message: Message):
    text = message.text
    lang = USER_LANG.get(message.from_user.id, "en")
    if text in (tr("menu.btn.tariffs", "ru"), tr("menu.btn.tariffs", "en")):
        await message.answer(tr("tariffs.title", lang))
        await message.answer(tr("tariffs.prompt", lang), reply_markup=tariffs_keyboard(lang))
    elif text in (tr("menu.btn.lang", "ru"), tr("menu.btn.lang", "en")):
        await handle_lang_cmd(message)
    elif text in (tr("menu.btn.help", "ru"), tr("menu.btn.help", "en")):
        await handle_help_cmd(message)

async def on_plan_clicked(cb: CallbackQuery, state: FSMContext):
    _, code = cb.data.split(":", 1)
    lang = USER_LANG.get(cb.from_user.id, "en")
    t = next((x for x in TARIFFS if x["code"] == code), None)
    if t:
        await cb.message.answer(tr("plan.chosen", lang,
                                   title=t["title_ru"] if lang == "ru" else t["title_en"],
                                   price=t["price"], days=t["days"]))
    await cb.answer()
    await cb.message.answer(payment_instructions_text(lang), reply_markup=payment_keyboard(lang, code))

async def on_proof_button(cb: CallbackQuery, state: FSMContext):
    _, code = cb.data.split(":", 1)
    await state.update_data(tariff_code=code)
    await state.set_state(ProofStates.waiting_for_proof)
    lang = USER_LANG.get(cb.from_user.id, "en")
    prompt = "Отправьте хэш транзакции или приложите скриншот/файл." if lang == "ru" else "Send the transaction hash or attach a screenshot/file."
    await cb.message.answer(prompt)
    await cb.answer()

def _store_payment_record(record: Dict[str, Any]) -> str:
    payments = load_payments()
    payment_id = str(int(time.time() * 1000))
    payments[payment_id] = record
    save_payments(payments)
    return payment_id

async def _send_admin_card(bot: Bot, payment_id: str, record: Dict[str, Any]) -> None:
    lang = record.get("lang", "ru")
    uname = record.get("username") or f"id:{record['user_id']}"
    t = next((x for x in TARIFFS if x["code"] == record["tariff_code"]), None)
    if t:
        tline = f"{t['title_ru']} / {t['price']} USDT / {t['days']} дней" if lang == "ru" else f"{t['title_en']} / {t['price']} USDT / {t['days']} days"
    else:
        tline = record.get("tariff_code", "")
    hash_text = record.get("hash")
    hash_line = f"🔗 Хэш: <code>{hash_text}</code>" if hash_text else ""
    text = tr("admin.new_payment", lang, uname=uname, tline=tline, hash_line=hash_line)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=tr("admin.paid_btn", lang), callback_data=f"paid:{payment_id}"),
        InlineKeyboardButton(text=tr("admin.rej_btn", lang), callback_data=f"rej:{payment_id}")
    ]])
    try:
        if record.get("photo_file_id"):
            await bot.send_photo(ADMIN_CHANNEL_ID_INT, photo=record["photo_file_id"], caption=text, parse_mode=ParseMode.HTML, reply_markup=kb)
        elif record.get("doc_file_id"):
            await bot.send_document(ADMIN_CHANNEL_ID_INT, document=record["doc_file_id"], caption=text, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await bot.send_message(ADMIN_CHANNEL_ID_INT, text, parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception as e:
        await bot.send_message(ADMIN_CHANNEL_ID_INT, f"⚠️ error sending admin card: {e}")

async def receive_proof(message: Message, state: FSMContext):
    data = await state.get_data()
    code = data.get("tariff_code")
    lang = USER_LANG.get(message.from_user.id, "en")
    user = message.from_user
    uname = f"@{user.username}" if user.username else None

    hash_text: Optional[str] = None
    photo_id: Optional[str] = None
    doc_id: Optional[str] = None

    if message.text and len(message.text.strip()) >= 5:
        hash_text = message.text.strip()
    if message.photo:
        photo_id = message.photo[-1].file_id
    if message.document:
        doc_id = message.document.file_id

    record = {
        "user_id": user.id,
        "username": uname,
        "tariff_code": code,
        "hash": hash_text,
        "photo_file_id": photo_id,
        "doc_file_id": doc_id,
        "status": "pending",
        "created_at": int(time.time()),
        "lang": lang
    }

    payment_id = _store_payment_record(record)
    await _send_admin_card(message.bot, payment_id, record)
    await message.answer(tr("proof.received", lang))
    await state.clear()

async def admin_paid(cb: CallbackQuery):
    try:
        _, payment_id = cb.data.split(":", 1)
    except Exception:
        await cb.answer("Bad payload", show_alert=True)
        return

    if ADMIN_IDS and cb.from_user.id not in ADMIN_IDS:
        await cb.answer("Нет прав", show_alert=True)
        return

    payments = load_payments()
    rec = payments.get(payment_id)
    if not rec:
        await cb.answer("Payment not found", show_alert=True)
        return

    rec["status"] = "confirmed"
    rec["confirmed_at"] = int(time.time())
    rec["admin_id"] = cb.from_user.id
    payments[payment_id] = rec
    save_payments(payments)

    invite_text = ""
    if TARGET_CHAT_ID:
        try:
            invite = await cb.message.bot.create_chat_invite_link(
                chat_id=int(TARGET_CHAT_ID), name=f"sub-{rec['user_id']}",
                expire_date=int(time.time()) + 3600, member_limit=1
            )
            invite_text = invite.invite_link
        except Exception as e:
            invite_text = "(failed to create invite)"
            await cb.message.answer(f"⚠️ Cannot create invite: {e}")

    lang = rec.get("lang", "en")
    text_user = tr("user.paid_confirmed", lang, invite_text=invite_text or "")
    try:
        await cb.message.bot.send_message(chat_id=rec["user_id"], text=text_user)
    except Exception as e:
        await cb.message.answer(f"Не удалось отправить пользователю: {e}")

    await cb.answer("OK")

async def admin_reject(cb: CallbackQuery):
    try:
        _, payment_id = cb.data.split(":", 1)
    except Exception:
        await cb.answer("Bad payload", show_alert=True)
        return

    if ADMIN_IDS and cb.from_user.id not in ADMIN_IDS:
        await cb.answer("Нет прав", show_alert=True)
        return

    payments = load_payments()
    rec = payments.get(payment_id)
    if not rec:
        await cb.answer("Payment not found", show_alert=True)
        return

    rec["status"] = "rejected"
    rec["rejected_at"] = int(time.time())
    rec["admin_id"] = cb.from_user.id
    payments[payment_id] = rec
    save_payments(payments)

    lang = rec.get("lang", "en")
    try:
        await cb.message.bot.send_message(chat_id=rec["user_id"], text=tr("user.rejected", lang))
    except Exception as e:
        await cb.message.answer(f"Не удалось отправить пользователю: {e}")

    await cb.answer("OK")

# ========== wiring / app ==========
async def main():
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # system commands
    await bot.set_my_commands([
        BotCommand(command="menu", description="Меню / Menu"),
        BotCommand(command="lang", description="Сменить язык / Change language"),
        BotCommand(command="ping", description="Проверка связи / Ping"),
        BotCommand(command="help", description="Помощь / Help"),
    ])

    # register handlers
    dp.message.register(handle_start, CommandStart())
    dp.message.register(handle_ping, Command("ping"))
    dp.message.register(handle_menu_cmd, Command("menu"))
    dp.message.register(handle_lang_cmd, Command("lang"))
    dp.message.register(handle_help_cmd, Command("help"))

    dp.callback_query.register(on_plan_clicked, F.data.startswith("plan:"))
    dp.callback_query.register(on_proof_button, F.data.startswith("proof:"))

    dp.message.register(handle_lang, F.text.in_(["Русский", "English"]))
    dp.message.register(handle_menu_buttons, F.text.in_([
        tr("menu.btn.tariffs", "ru"), tr("menu.btn.tariffs", "en"),
        tr("menu.btn.lang", "ru"), tr("menu.btn.lang", "en"),
        tr("menu.btn.help", "ru"), tr("menu.btn.help", "en"),
    ]))

    dp.message.register(receive_proof, ProofStates.waiting_for_proof)

    # admin callbacks
    dp.callback_query.register(admin_paid, F.data.startswith("paid:"))
    dp.callback_query.register(admin_reject, F.data.startswith("rej:"))

    print("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
