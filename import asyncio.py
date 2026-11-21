import asyncio
import json
import os
import urllib.parse
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import WebAppInfo, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАСТРОЙКИ ---
BOT_TOKEN = "9135366727:AAFckscPos9tTBgJ-MQYKARlL2vMh5cFyrw"
ADMIN_IDS = [8624408698, 7088402556]
WEBAPP_URL = "https://selenaandenan.github.io/zombi-777/"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
DB_FILE = "zombi_db.json"

# --- БАЗА ДАННЫХ ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"users": {}, "jackpot": 5000, "withdrawals": []}

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

db = load_db()

def get_user(user_id):
    uid = str(user_id)
    if uid not in db["users"]:
        db["users"][uid] = {
            "balance": 0,
            "total_deposits": 0,
            "total_withdrawals": 0,
            "games": 0,
            "wins": 0,
            "losses": 0,
            "username": ""
        }
        save_db(db)
    return db["users"][uid]

def update_balance(user_id, amount):
    uid = str(user_id)
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
    
    # Формируем параметры для Mini App
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
        f"⚠️ Казино забирает своё. Играй осторожно.\n\n"
        f"Жми кнопку ниже, чтобы начать!"
    )
    
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=main_kb(start_param)
    )

@dp.callback_query(F.data == "pay_stars")
async def send_invoice(callback: types.CallbackQuery):
    await callback.message.answer_invoice(
        title="Пополнение Zombi 777",
        description="Покупка 100 игровых звезд",
        prices=[LabeledPrice(label="Stars", amount=100)],
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
    user = get_user(message.from_user.id)
    update_balance(message.from_user.id, add_amount)
    user["total_deposits"] += add_amount
    save_db(db)
    
    await message.answer(
        f"✅ **УСПЕШНО!**\n\n"
        f"Ваш баланс пополнен на **{add_amount}** ⭐\n"
        f"Новый баланс: **{user['balance']}** ⭐\n\n"
        f"Удачи в играх! 🧟",
        parse_mode="Markdown",
        reply_markup=main_kb()
    )

@dp.callback_query(F.data == "withdraw_req")
async def withdraw_request(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    await callback.message.answer(
        f"💸 **ВЫВОД СРЕДСТВ**\n\n"
        f"💰 Ваш баланс: **{user['balance']}** ⭐\n"
        f"📊 Минимальная сумма: **500** ⭐\n\n"
        f"📝 Отправьте сообщение в формате:\n"
        f"`СУММА РЕКВИЗИТЫ`\n\n"
        f"Пример: `1000 2200123456789`",
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "show_profile")
async def show_profile(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    win_rate = (user["wins"] / user["games"] * 100) if user["games"] > 0 else 0
    
    text = (
        f"👤 **ВАШ ПРОФИЛЬ**\n\n"
        f"🆔 ID: `{callback.from_user.id}`\n"
        f"👤 Имя: {callback.from_user.first_name}\n\n"
        f"💰 **БАЛАНС:** {user['balance']} ⭐\n\n"
        f"📊 **СТАТИСТИКА:**\n"
        f"├ Пополнено: {user['total_deposits']} ⭐\n"
        f"├ Выведено: {user['total_withdrawals']} ⭐\n"
        f"├ Игр сыграно: {user['games']}\n"
        f"├ Побед: {user['wins']}\n"
        f"├ Поражений: {user['losses']}\n"
        f"└ Винрейт: {win_rate:.1f}%\n\n"
        f"🔥 Джекпот: {db['jackpot']} ⭐"
    )
    
    await callback.message.answer(text, parse_mode="Markdown")

@dp.message(F.chat.type == "private")
async def process_withdraw_text(message: types.Message):
    if message.text.startswith("/") or len(message.text.strip()) < 5:
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) >= 2:
        try:
            amount = int(parts[0])
            reqs = parts[1]
            user = get_user(message.from_user.id)
            
            if amount < 500:
                await message.answer("❌ Минимальная сумма вывода: **500** ⭐", parse_mode="Markdown")
                return
            
            if user["balance"] < amount:
                await message.answer("❌ **Недостаточно средств!**", parse_mode="Markdown")
                return
            
            # Списываем баланс
            update_balance(message.from_user.id, -amount)
            user["total_withdrawals"] += amount
            save_db(db)
            
            # Создаем заявку
            withdrawal = {
                "id": len(db["withdrawals"]) + 1,
                "user_id": message.from_user.id,
                "username": message.from_user.first_name,
                "amount": amount,
                "requirements": reqs,
                "status": "pending",
                "date": str(message.date)
            }
            db["withdrawals"].append(withdrawal)
            save_db(db)
            
            await message.answer(
                f"✅ **Заявка на вывод создана!**\n\n"
                f"💰 Сумма: **{amount}** ⭐\n"
                f"💳 Реквизиты: `{reqs}`\n\n"
                f"⏳ Ожидайте подтверждения администратора.",
                parse_mode="Markdown"
            )
            
            # Уведомление админам
            notif = (
                f"🚨 **НОВАЯ ЗАЯВКА НА ВЫВОД** 🚨\n\n"
                f"🆔 ID: `{message.from_user.id}`\n"
                f"👤 Имя: {message.from_user.first_name}\n"
                f"💰 Сумма: **{amount}** ⭐\n"
                f"💳 Реквизиты: `{reqs}`\n"
                f"📅 Дата: {message.date}\n\n"
                f"№ Заявки: {withdrawal['id']}"
            )
            
            for admin_id in ADMIN_IDS:
                try:
                    kb = InlineKeyboardBuilder()
                    kb.button(text="✅ Выдать", callback_data=f"approve_{withdrawal['id']}")
                    kb.button(text="❌ Отклонить", callback_data=f"reject_{withdrawal['id']}")
                    kb.button(text="⚠️ Вернуть", callback_data=f"return_{withdrawal['id']}")
                    kb.adjust(3)
                    await bot.send_message(admin_id, notif, parse_mode="Markdown", reply_markup=kb.as_markup())
                except Exception as e:
                    print(f"Ошибка отправки админу {admin_id}: {e}")
                    
        except ValueError:
            pass

@dp.callback_query(F.data.startswith("approve_"))
async def approve_withdraw(callback: types.CallbackQuery):
    withdraw_id = int(callback.data.split("_")[1])
    
    for w in db["withdrawals"]:
        if w["id"] == withdraw_id and w["status"] == "pending":
            w["status"] = "approved"
            save_db(db)
            
            await callback.message.edit_text(
                f"✅ **ВЫВОД ОДОБРЕН**\n\n"
                f"ID: {w['user_id']}\n"
                f"Сумма: {w['amount']} ⭐\n"
                f"Реквизиты: {w['requirements']}\n\n"
                f"Статус: ✅ Выдано"
            )
            
            await bot.send_message(
                w["user_id"],
                f"💸 **ВЫПЛАТА ОДОБРЕНА!**\n\n"
                f"Средства **{w['amount']}** ⭐ отправлены на ваши реквизиты.\n\n"
                f"Спасибо за игру в Zombi 777! 🧟",
                parse_mode="Markdown"
            )
            break
    
    await callback.answer()

@dp.callback_query(F.data.startswith("reject_"))
async def reject_withdraw(callback: types.CallbackQuery):
    withdraw_id = int(callback.data.split("_")[1])
    
    for w in db["withdrawals"]:
        if w["id"] == withdraw_id and w["status"] == "pending":
            w["status"] = "rejected"
            save_db(db)
            
            await callback.message.edit_text(
                f"❌ **ВЫВОД ОТКЛОНЕН**\n\n"
                f"ID: {w['user_id']}\n"
                f"Сумма: {w['amount']} ⭐\n"
                f"Реквизиты: {w['requirements']}\n\n"
                f"Статус: ❌ Отклонено"
            )
            
            await bot.send_message(
                w["user_id"],
                f"❌ **ВЫВОД ОТКЛОНЕН**\n\n"
                f"Заявка на **{w['amount']}** ⭐ отклонена администратором.\n"
                f"Проверьте корректность реквизитов и создайте новую заявку.",
                parse_mode="Markdown"
            )
            break
    
    await callback.answer()

@dp.callback_query(F.data.startswith("return_"))
async def return_withdraw(callback: types.CallbackQuery):
    withdraw_id = int(callback.data.split("_")[1])
    
    for w in db["withdrawals"]:
        if w["id"] == withdraw_id and w["status"] == "pending":
            w["status"] = "returned"
            # Возвращаем средства
            update_balance(w["user_id"], w["amount"])
            user = get_user(w["user_id"])
            user["total_withdrawals"] -= w["amount"]
            save_db(db)
            
            await callback.message.edit_text(
                f"↩️ **СРЕДСТВА ВОЗВРАЩЕНЫ**\n\n"
                f"ID: {w['user_id']}\n"
                f"Сумма: {w['amount']} ⭐\n"
                f"Реквизиты: {w['requirements']}\n\n"
                f"Статус: ↩️ Возвращено на баланс"
            )
            
            await bot.send_message(
                w["user_id"],
                f"↩️ **СРЕДСТВА ВОЗВРАЩЕНЫ**\n\n"
                f"Заявка на вывод **{w['amount']}** ⭐ отменена.\n"
                f"Средства возвращены на ваш баланс.",
                parse_mode="Markdown"
            )
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
    except Exception as e:
        print(f"WebApp Error: {e}")

# --- АДМИН КОМАНДЫ ---

@dp.message(F.from_user.id.in_(ADMIN_IDS) & F.text == "/stats")
async def admin_stats(message: types.Message):
    total_users = len(db["users"])
    total_balance = sum(u["balance"] for u in db["users"].values())
    total_deposits = sum(u["total_deposits"] for u in db["users"].values())
    total_withdrawals = sum(u["total_withdrawals"] for u in db["users"].values())
    total_games = sum(u["games"] for u in db["users"].values())
    pending_withdrawals = len([w for w in db["withdrawals"] if w["status"] == "pending"])
    
    text = (
        f"📊 **СТАТИСТИКА КАЗИНО**\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"💰 Общий баланс: {total_balance} ⭐\n"
        f"💳 Всего пополнено: {total_deposits} ⭐\n"
        f"💸 Всего выведено: {total_withdrawals} ⭐\n"
        f"🎮 Всего игр: {total_games}\n"
        f"🔥 Джекпот: {db['jackpot']} ⭐\n"
        f"⏳ Ожидают вывода: {pending_withdrawals}\n\n"
        f"💵 **Прибыль казино:** {total_deposits - total_withdrawals} ⭐"
    )
    
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.from_user.id.in_(ADMIN_IDS) & F.text.startswith("/give"))
async def admin_give(message: types.Message):
    try:
        parts = message.text.split()
        user_id = parts[1]
        amount = int(parts[2])
        
        user = get_user(int(user_id))
        update_balance(int(user_id), amount)
        
        await message.answer(f"✅ Начислено {amount} ⭐ пользователю {user_id}")
        await bot.send_message(int(user_id), f"🎁 Администратор начислил вам **{amount}** ⭐!", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(F.from_user.id.in_(ADMIN_IDS) & F.text.startswith("/take"))
async def admin_take(message: types.Message):
    try:
        parts = message.text.split()
        user_id = parts[1]
        amount = int(parts[2])
        
        user = get_user(int(user_id))
        update_balance(int(user_id), -amount)
        
        await message.answer(f"✅ Списано {amount} ⭐ у пользователя {user_id}")
        await bot.send_message(int(user_id), f"⚠️ Администратор списал **{amount}** ⭐ с вашего баланса!", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(F.from_user.id.in_(ADMIN_IDS) & F.text.startswith("/setjackpot"))
async def admin_setjackpot(message: types.Message):
    try:
        amount = int(message.text.split()[1])
        db["jackpot"] = amount
        save_db(db)
        await message.answer(f"✅ Джекпот установлен: {amount} ⭐")
    except:
        await message.answer("❌ Формат: /setjackpot СУММА")

if __name__ == "__main__":
    print("🧟 Zombi 777 Casino Bot Started...")
    asyncio.run(dp.start_polling(bot))
