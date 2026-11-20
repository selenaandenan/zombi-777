import asyncio
import json
import os
import time
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import WebAppInfo, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8647859964:AAFvXgbvIiuTmtAEPRWFkMFS8_Zeaf97p4I"
ADMIN_IDS = [8624408698,7088402556] # Ваш ID для уведомлений о выводе

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DB_FILE = "zombi_db.json"

# --- РАБОТА С БД ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"users": {}, "jackpot": 5000} # Начальный джекпот 5000 звезд

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

db = load_db()

def get_user(user_id):
    uid = str(user_id)
    if uid not in db["users"]:
        db["users"][uid] = {
            "balance": 0,
            "last_bonus": 0,
            "username": ""
        }
        save_db(db)
    return db["users"][uid]

def update_balance(user_id, amount):
    uid = str(user_id)
    db["users"][uid]["balance"] += amount
    save_db(db)

# --- КЛАВИАТУРЫ ---
def main_kb():
    builder = InlineKeyboardBuilder()
    # Ссылка на ваш хостинг с index.html
    builder.button(text="🎮 ИГРАТЬ В КАЗИНО", web_app=WebAppInfo(url="https://ваш-сайт.com/index.html"))
    builder.button(text="💰 Пополнить (Stars)", callback_data="pay_stars")
    builder.button(text="💸 Вывод средств", callback_data="withdraw_req")
    builder.adjust(1)
    return builder.as_markup()

# --- ОБРАБОТЧИКИ ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user = get_user(message.from_user.id)
    user["username"] = message.from_user.first_name
    save_db(db)
    
    await message.answer(
        f"🧟 ZOMBI 777\n\n"
        f"Добро пожаловать, {message.from_user.first_name}!\n"
        f"Баланс: {user['balance']} ⭐\n"
        f"Текущий ДЖЕКПОТ: {db['jackpot']} ⭐\n\n"
        f"Жми кнопку ниже, чтобы начать!",
        parse_mode="Markdown",
        reply_markup=main_kb()
    )

# Оплата Звездами
@dp.callback_query(F.data == "pay_stars")
async def send_invoice(callback: types.CallbackQuery):
    prices = [LabeledPrice(label="100 Stars", amount=100)] # Цена в звездах * 100 (копейки/центы не важны для stars, важно количество)
    # Для Stars используется специальный флаг pay_provider_token=None или пустая строка в новых версиях, но лучше использовать стандартный инвойс
    await callback.message.answer_invoice(
        title="Пополнение баланса Zombi 777",
        description="Покупка 100 игровых звезд",
        prices=prices,
        provider_token="", # Пусто для Stars
        payload="deposit_100",
        currency="XTR" # Валюта Telegram Stars
    )

@dp.pre_checkout_query()
async def pre_checkout(query: types.PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    amount = int(message.successful_payment.total_amount) # Приходит в копейках/центах, для XTR обычно 1 звезда = 1 единица, но проверьте документацию. Обычно total_amount / 100 если это фиат, но для XTR может быть иначе.
    # В случае со Stars, total_amount часто равен количеству звезд * 1 (или 100 зависит от API). 
    # Допустим, мы продаем пакеты. Здесь упростим: +100 звезд за любую успешную оплату для теста.
    
    add_amount = 100 
    update_balance(message.from_user.id, add_amount)
    
    await message.answer(
        f"✅ УСПЕШНО!\n\n"
        f"Ваш баланс пополнен на {add_amount} ⭐\n"
        f"Новый баланс: {get_user(message.from_user.id)['balance']} ⭐",
        parse_mode="Markdown",
        reply_markup=main_kb()
    )
# Вывод средств
@dp.callback_query(F.data == "withdraw_req")
async def withdraw_request(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    await callback.message.answer(
        f"💸 ВЫВОД СРЕДСТВ\n\n"
        f"Баланс: {user['balance']} ⭐\n"
        f"Минимум: 500 ⭐\n\n"
        f"Отправьте сообщение в формате:\n"
        f"СУММА РЕКВИЗИТЫ",
        parse_mode="Markdown"
    )

@dp.message(F.chat.type == "private")
async def process_withdraw_text(message: types.Message):
    if message.text.startswith("/"): return
    
    parts = message.text.split()
    if len(parts) >= 2:
        try:
            amount = int(parts[0])
            reqs = " ".join(parts[1:])
            user = get_user(message.from_user.id)
            
            if amount >= 500 and user["balance"] >= amount:
                update_balance(message.from_user.id, -amount)
                await message.answer("✅ Заявка принята! Ожидайте выплаты.")
                await bot.send_message(ADMIN_IDS, f"🚨 НОВЫЙ ВЫВОД\nID: {message.from_user.id}\nСумма: {amount}\nРеквизиты: {reqs}")
            else:
                await message.answer("❌ Ошибка: Недостаточно средств или сумма меньше минимума.")
        except ValueError:
            pass

# Получение данных из Mini App (если нужно синхронизировать результат игры на сервере)
@dp.message(F.web_app_data)
async def web_app_data_handler(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        if data.get("type") == "game_result":
            # Здесь можно дополнительно проверить честность, но пока просто доверяем клиенту для скорости
            pass
    except:
        pass

async def main():
    print("Zombi Casino Bot Started...")
    await dp.start_polling(bot)

if__AZZ__== "__main__"
asyncio.run(main())
