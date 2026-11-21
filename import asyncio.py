import asyncio
import json
import os
import urllib.parse
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import WebAppInfo, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАСТРОЙКИ (ЗАПОЛНИ ПРАВИЛЬНО!) ---
BOT_TOKEN = "9135366727:AAFckscPos9tTBgJ-MQYKARlL2vMh5cFyrw"
ADMIN_IDS = [8624408698, 7088402556]
WEBAPP_URL = "https://selenaandenan.github.io/zombi-777/"


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
DB_FILE = "zombi_db.json"

# --- БАЗА ДАННЫХ (СОХРАНЕНИЕ) ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {"users": {}, "jackpot": 5000, "withdrawals": []}

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

db = load_db()

def get_user(user_id):
    uid = str(user_id)
    if uid not in db["users"]:
        db["users"][uid] = {
            "balance": 0, "total_deposits": 0, "total_withdrawals": 0,
            "games": 0, "wins": 0, "losses": 0, "username": ""
        }
        save_db(db)
    return db["users"][uid]

def update_balance(user_id, amount):
    uid = str(user_id)
    if uid in db["users"]:
        db["users"][uid]["balance"] += amount
        save_db(db)

# --- КЛАВИАТУРЫ ---
def main_kb(start_param=""):
    builder = InlineKeyboardBuilder()
    url = WEBAPP_URL if not start_param else f"{WEBAPP_URL}?startapp={start_param}"
    builder.button(text="🎮 ИГРАТЬ В КАЗИНО", web_app=WebAppInfo(url=url))
    builder.button(text="💰 Пополнить (Stars)", callback_data="pay_stars")
    builder.button(text="💸 Вывод средств", callback_data="withdraw_req")
    builder.button(text="👤 Профиль", callback_data="show_profile")
    builder.adjust(1)
    return builder.as_markup()

# --- ОБРАБОТЧИКИ ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user = get_user(message.from_user.id)
    user["username"] = message.from_user.first_name
    save_db(db)
    
    params = {
        "balance": user["balance"],
        "deposits": user["total_deposits"],
        "withdrawals": user["total_withdrawals"],
        "games": user["games"],
        "wins": user["wins"],
        "losses": user["losses"]
    }
    start_param = urllib.parse.quote(json.dumps(params))
    
    text = (
        f"🧟 **ZOMBI 777 CASINO** 🧟\n\n"
        f"Привет, {message.from_user.first_name}!\n"
        f"💀 Твой баланс: **{user['balance']}** ⭐\n"
        f"🔥 ДЖЕКПОТ СЕЙФА: **{db['jackpot']}** ⭐\n\n"
        f"⚠️ Казино забирает своё. Играй осторожно."
    )
    
    await message.answer(text, parse_mode="Markdown", reply_markup=main_kb(start_param))

@dp.callback_query(F.data == "pay_stars")
async def send_invoice(callback: types.CallbackQuery):
    await callback.message.answer_invoice(
        title="Пополнение Zombi 777", description="100 игровых звезд",
        prices=[LabeledPrice(label="Stars", amount=100)],
        provider_token="", payload="deposit_100", currency="XTR"
    )

@dp.pre_checkout_query()
async def pre_checkout(query: types.PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    add_amount = 100
    user = get_user(message.from_user.id)
    update_balance(message.from_user.id, add_amount)
    user["total_deposits"] += add_amount
    save_db(db)
    
    await message.answer(
        f"✅ **УСПЕШНО!** +{add_amount} ⭐\nНовый баланс: {user['balance']} ⭐",
        parse_mode="Markdown", reply_markup=main_kb()
    )

@dp.callback_query(F.data == "withdraw_req")
async def withdraw_request(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    await callback.message.answer(
        f"💸 **ВЫВОД СРЕДСТВ**\n\n"
        f"Баланс: {user['balance']} ⭐ | Минимум: 500 ⭐\n\n"
        f"Отправьте сообщение:\n`СУММА РЕКВИЗИТЫ`",
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "show_profile")
async def show_profile(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    win_rate = (user["wins"] / max(user["games"], 1) * 100)
    
    text = (
        f"👤 **ПРОФИЛЬ**\n\n"
        f"ID: `{callback.from_user.id}`\n"
        f"💰 Баланс: {user['balance']} ⭐\n"
        f"📊 Игр: {user['games']} | Побед: {user['wins']}\n"
        f"📈 Винрейт: {win_rate:.1f}%\n"
        f"🔥 Джекпот: {db['jackpot']} ⭐"
    )
    await callback.message.answer(text, parse_mode="Markdown")

@dp.message(F.chat.type == "private")
async def process_withdraw_text(message: types.Message):
    if message.text.startswith("/") or len(message.text.strip()) < 5: return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) >= 2:
        try:
            amount = int(parts[0])
            reqs = parts[1]
            user = get_user(message.from_user.id)
            
            if amount < 500:
                return await message.answer("❌ Минимум: 500 ⭐")
            if user["balance"] < amount:
                return await message.answer("❌ Недостаточно средств!")
            
            update_balance(message.from_user.id, -amount)
            user["total_withdrawals"] += amount
            
            withdrawal = {
                "id": len(db["withdrawals"]) + 1,
                "user_id": message.from_user.id,
                "username": message.from_user.first_name,
                "amount": amount, "requirements": reqs,
                "status": "pending", "date": str(message.date)
            }
            db["withdrawals"].append(withdrawal)
            save_db(db)
            
            await message.answer(f"✅ Заявка #{withdrawal['id']} создана! Ожидайте.")
            
            notif = f"🚨 ВЫВОД #{withdrawal['id']}\nID: {message.from_user.id}\nСумма: {amount} ⭐\nРеквизиты: {reqs}"
            for admin_id in ADMIN_IDS:
                try:
                    kb = InlineKeyboardBuilder()
                    kb.button(text="✅ Выдать", callback_data=f"approve_{withdrawal['id']}")
                    kb.button(text="❌ Отклонить", callback_data=f"reject_{withdrawal['id']}")
                    kb.button(text="↩️ Вернуть", callback_data=f"return_{withdrawal['id']}")
                    kb.adjust(3)
                    await bot.send_message(admin_id, notif, reply_markup=kb.as_markup())
                except: pass
        except ValueError: pass

# --- АДМИНКА (Безопасная проверка ID) ---

@dp.message(Command("stats"))
async def admin_stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    
    total_users = len(db["users"])
    total_bal = sum(u["balance"] for u in db["users"].values())
    total_dep = sum(u["total_deposits"] for u in db["users"].values())
    total_wit = sum(u["total_withdrawals"] for u in db["users"].values())
    pending = len([w for w in db["withdrawals"] if w["status"] == "pending"])
    
    await message.answer(
        f"📊 **СТАТИСТИКА**\n\n"
        f"👥 Юзеров: {total_users}\n"
        f"💰 Общий баланс: {total_bal} ⭐\n"
        f"💳 Пополнено: {total_dep} ⭐\n"
        f"💸 Выведено: {total_wit} ⭐\n"
        f"⏳ Ожидают: {pending}\n"
        f"💵 Прибыль: {total_dep - total_wit} ⭐",
        parse_mode="Markdown"
    )

@dp.message(Command("give"))
async def admin_give(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        _, uid, amt = message.text.split()
        update_balance(int(uid), int(amt))
        await message.answer(f"✅ Начислено {amt} ⭐ юзеру {uid}")
        await bot.send_message(int(uid), f"🎁 Админ начислил {amt} ⭐!")
    except: await message.answer("❌ Формат: /give ID СУММА")

@dp.message(Command("setjackpot"))
async def admin_setjackpot(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        db["jackpot"] = int(message.text.split()[1])
        save_db(db)
        await message.answer(f"✅ Джекпот: {db['jackpot']} ⭐")
    except: await message.answer("❌ Формат: /setjackpot СУММА")

@dp.callback_query(F.data.startswith(("approve_", "reject_", "return_")))
async def handle_withdraw_actions(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return await callback.answer("⛔ Нет прав!", show_alert=True)
        
    action, wid = callback.data.split("_")
    wid = int(wid)
    
    for w in db["withdrawals"]:
        if w["id"] == wid and w["status"] == "pending":
            if action == "approve":
                w["status"] = "approved"
                await bot.send_message(w["user_id"], f"💸 Выплата {w['amount']} ⭐ одобрена!")
                await callback.message.edit_text(f"✅ Выдано: {w['amount']} ⭐ ({w['username']})")
            elif action == "reject":
                w["status"] = "rejected"
                await bot.send_message(w["user_id"], f"❌ Вывод {w['amount']} ⭐ отклонен.")
                await callback.message.edit_text(f"❌ Отклонено: {w['amount']} ⭐ ({w['username']})")
            elif action == "return":
                w["status"] = "returned"
                update_balance(w["user_id"], w["amount"])
                user = get_user(w["user_id"])
                user["total_withdrawals"] -= w["amount"]
                save_db(db)
                await bot.send_message(w["user_id"], f"↩️ Средства {w['amount']} ⭐ возвращены!")
                await callback.message.edit_text(f"↩️ Возврат: {w['amount']} ⭐ ({w['username']})")
            save_db(db)
            break
    await callback.answer()

@dp.message(F.web_app_data)
async def web_app_data_handler(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        if data.get("action") == "update_profile":
            p = data.get("data", {})
            uid = str(message.from_user.id)
            user = db["users"][uid]
            user["balance"] = int(p.get("balance", 0))
            user["games"] = int(p.get("games", 0))
            user["wins"] = int(p.get("wins", 0))
            user["losses"] = int(p.get("losses", 0))
            save_db(db)
    except Exception as e: print(f"WebApp Error: {e}")

if __name__ == "__main__":
    print("🧟 Zombi 777 Started...")
    asyncio.run(dp.start_polling(bot))
    
