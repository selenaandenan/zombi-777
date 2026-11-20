iimport asyncio
import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import WebAppInfo, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8647859964:AAFvXgbvIiuTmtAEPRWFkMFS8_Zeaf97p4I"
ADMIN_IDS = [8624408698, 7088402556] 
WEBAPP_URL = "https://github.com/selenaandenan/AZZZZ/blob/ac30dbd7b70868f3073d6c9faebbb00a445df3fb/AZZ.html" # ⚠️ ЗАМЕНИ НА СВОЮ ССЫЛКУ

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DB_FILE = "zombi_db.json"

# --- РАБОТА С БД ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"users": {}, "jackpot": 5000}

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
    builder.button(text="🎮 ИГРАТЬ В КАЗИНО", web_app=WebAppInfo(url=WEBAPP_URL))
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

@dp.callback_query(F.data == "pay_stars")
async def send_invoice(callback: types.CallbackQuery):
    prices = [LabeledPrice(label="100 Stars", amount=100)]
    await callback.message.answer_invoice(
        title="Пополнение баланса Zombi 777",
        description="Покупка 100 игровых звезд",
        prices=prices,
        provider_token="",
        payload="deposit_100",
        currency="XTR"
    )

@dp.pre_checkout_query()
async def pre_checkout(query: types.PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    add_amount = 100 
    update_balance(message.from_user.id, add_amount)
    
    await message.answer(
        f"✅ УСПЕШНО!\n\n"
        f"Ваш баланс пополнен на {add_amount} ⭐\n"
        f"Новый баланс: {get_user(message.from_user.id)['balance']} ⭐",
        parse_mode="Markdown",
        reply_markup=main_kb()
    )

@dp.callback_query(F.data == "withdraw_req")
async def withdraw_request(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    await callback.message.answer(
        f"💸 ВЫВОД СРЕДСТВ\n\n"
        f"Баланс: {user['balance']} ⭐\n"
        f"Минимум: 500 ⭐\n\n"
        f"Отправьте сообщение в формате:\n"
        f"`СУММА РЕКВИЗИТЫ`",
        parse_mode="Markdown"
    )

@dp.message(F.chat.type == "private")
async def process_withdraw_text(message: types.Message):
    if message.text.startswith("/"): 
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) >= 2:
        try:
            amount = int(parts[0])
            reqs = parts[1]
            user = get_user(message.from_user.id)
            
            if amount >= 500 and user["balance"] >= amount:
                update_balance(message.from_user.id, -amount)
                await message.answer("✅ Заявка принята! Ожидайте выплаты.")
                
                # ✅ ИСПРАВЛЕНО: Отправляем уведомление каждому админу отдельно
                notification = (
                    f"🚨 НОВЫЙ ВЫВОД\n"
                    f"ID: {message.from_user.id}\n"
                    f"Имя: {message.from_user.first_name}\n"
                    f"Сумма: {amount} ⭐\n"
                    f"Реквизиты: {reqs}"
                )
                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(admin_id, notification)
                    except Exception:
                        pass
                        
            else:
                await message.answer("❌ Ошибка: Недостаточно средств или сумма меньше минимума.")
        except ValueError:
            pass

@dp.message(F.web_app_data)
async def web_app_data_handler(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        action = data.get("action")
        
        if action == "win":
            win_amount = int(data.get("amount", 0))
            update_balance(message.from_user.id, win_amount)
            
    except Exception:
        pass

# ✅ ИСПРАВЛЕНО: Правильный синтаксис запуска
if __name__ == "__main__":
    print("Zombi Casino Bot Started...")
    asyncio.run(main())
