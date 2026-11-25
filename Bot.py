import asyncio
import logging
import random
import sqlite3
import json
from datetime import datetime

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

# ==========================================
# ⚠️ НАСТРОЙКИ - ВПИШИ СВОИ ДАННЫЕ СЮДА ⚠️
# ==========================================

# Токен бота от @BotFather
BOT_TOKEN = "9135366727:AAFckscPos9tTBgJ-MQYKARlL2vMh5cFyrw"

# ID или юзернейм канала
CHANNEL_ID = "-1002170802203"
CHANNEL_LINK = "https://t.me/sugarlolypop"

# ID админов через запятую
ADMIN_IDS = [8624408698, 7088402556]

# ⚠️ ССЫЛКА НА ТВОЙ САЙТ (WebApp) ⚠️
GAME_URL = "https://selenaandenan.github.io/zombi-777/"

# ==========================================

DB_FILE = "casino_stars.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# --- БАЗА ДАННЫХ (SQLite) ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance_stars INTEGER DEFAULT 0,
        is_subscribed INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        details TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT
    )''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, ""))
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = c.fetchone()
    conn.close()
    return dict(user) if user else None

def update_balance(user_id, amount):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET balance_stars = balance_stars + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def add_withdrawal(user_id, amount, details):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO withdrawals (user_id, amount, details, created_at) VALUES (?, ?, ?, ?)",
              (user_id, amount, details, now))
    conn.commit()
    conn.close()

# --- СОСТОЯНИЯ (FSM) ---
class PayState(StatesGroup):
    waiting_for_amount = State()

# --- ПРОВЕРКА ПОДПИСКИ ---
async def check_subscription(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {e}")
        return False

# --- КЛАВИАТУРЫ ---
def get_main_kb():
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🎮 ИГРАТЬ"), KeyboardButton(text="💰 Баланс")],
        [KeyboardButton(text="💸 Вывод средств"), KeyboardButton(text="⭐ Пополнить")]
    ], resize_keyboard=True)
    return kb

def get_check_sub_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")],
        [InlineKeyboardButton(text="🔗 Перейти в канал", url=CHANNEL_LINK)]
    ])

def get_game_numbers_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣", callback_data="num_1"), InlineKeyboardButton(text="2️⃣", callback_data="num_2"), InlineKeyboardButton(text="3️⃣", callback_data="num_3")],
        [InlineKeyboardButton(text="4️⃣", callback_data="num_4"), InlineKeyboardButton(text="5️⃣", callback_data="num_5")]
    ])

# --- ОБРАБОТЧИКИ ---

@router.message(CommandStart())
async def cmd_start(message: Message):
    user = get_user(message.from_user.id)
    is_sub = await check_subscription(message.from_user.id)
    
    if is_sub:
        if not user['is_subscribed']:
            conn = sqlite3.connect(DB_FILE)
            conn.execute("UPDATE users SET is_subscribed = 1 WHERE user_id = ?", (message.from_user.id,))
            conn.commit()
            conn.close()
            
        await message.answer(
            f"👋 Привет, {message.from_user.first_name}!\n"
            f"Твой баланс: {user['balance_stars']} ⭐\n\n"
            f"Выбери действие в меню ниже 👇",
            reply_markup=get_main_kb()
        )
    else:
        await message.answer(
            "🚫 **ДОСТУП ЗАКРЫТ**\n\n"
            "Для использования бота необходимо подписаться на наш канал:",
            reply_markup=get_check_sub_kb(),
            parse_mode="Markdown"
        )

@router.callback_query(F.data == "check_sub")
async def cb_check_sub(callback: CallbackQuery):
    is_sub = await check_subscription(callback.from_user.id)
    if is_sub:
        conn = sqlite3.connect(DB_FILE)
        conn.execute("UPDATE users SET is_subscribed = 1 WHERE user_id = ?", (callback.from_user.id,))
        conn.commit()
        conn.close()
        
        await callback.message.edit_text("✅ Спасибо за подписку! Доступ открыт.")
        await callback.message.answer(
            f"👋 Добро пожаловать!\nБаланс: {get_user(callback.from_user.id)['balance_stars']} ⭐",
            reply_markup=get_main_kb()
        )
    else:
        await callback.answer("❌ Вы еще не подписались!", show_alert=True)

# --- ИГРА (ТЕКСТОВАЯ, как запасной вариант) ---
@router.message(F.text == "🎲 Играть (1-5)")
async def game_start(message: Message):
    user = get_user(message.from_user.id)
    if user['balance_stars'] < 10:
        return await message.answer("❌ Недостаточно звезд для игры. Минимальная ставка 10 ⭐.")
    
    await message.answer(
        "🎲 **ИГРА 'УГАДАЙ ЧИСЛО'**\n\n"
        "Выберите число от 1 до 5.\nСтавка: **10 ⭐** | Выигрыш: **30 ⭐** (x3)",
        reply_markup=get_game_numbers_kb(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("num_"))
async def game_play(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    bet_amount = 10
    win_multiplier = 3
    
    if user['balance_stars'] < bet_amount:
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        return

    chosen_num = int(callback.data.split("_")[1])
    secret_num = random.randint(1, 5)
    update_balance(callback.from_user.id, -bet_amount)
    
    if chosen_num == secret_num:
        win = bet_amount * win_multiplier
        update_balance(callback.from_user.id, win)
        text = f"🎉 **ПОБЕДА!**\nВыпало число: {secret_num}\nВы выиграли {win} ⭐!"
        await callback.message.edit_text(text, parse_mode="Markdown")
    else:
        text = f"💀 **ПРОИГРЫШ**\nВы выбрали: {chosen_num}\nВыпало: {secret_num}"
        await callback.message.edit_text(text, parse_mode="Markdown")
    
    await callback.message.answer("Сыграть еще?", reply_markup=get_game_numbers_kb())

# --- БАЛАНС ---
@router.message(F.text == "💰 Баланс")
async def show_balance(message: Message):
    user = get_user(message.from_user.id)
    await message.answer(f"💳 Ваш баланс: **{user['balance_stars']}** ⭐", parse_mode="Markdown")

# --- ОПЛАТА (STARS) ---
@router.message(F.text == "⭐ Пополнить")
async def pay_start(message: Message, state: FSMContext):
    await message.answer("💸 Введите количество звезд для пополнения (минимум 50):")
    await state.set_state(PayState.waiting_for_amount)

@router.message(PayState.waiting_for_amount)
async def process_pay_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount < 50:
            return await message.answer("❌ Минимальная сумма пополнения 50 ⭐.")
        
        prices = [LabeledPrice(label=f"{amount} Stars", amount=amount)]
        await message.answer_invoice(
            title=f"Пополнение баланса на {amount} ⭐",
            description=f"Покупка {amount} игровых звезд",
            prices=prices,
            provider_token="",
            payload=f"deposit_{amount}",
            currency="XTR"
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число.")

@router.pre_checkout_query()
async def pre_checkout(query):
    await query.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    amount = int(payload.split("_")[1])
    update_balance(message.from_user.id, amount)
    
    await message.answer(
        f"✅ **УСПЕШНО!**\n\n"
        f"Баланс пополнен на {amount} ⭐\n"
        f"Новый баланс: {get_user(message.from_user.id)['balance_stars']} ⭐",
        parse_mode="Markdown",
        reply_markup=get_main_kb()
    )

# --- ВЫВОД СРЕДСТВ (ИСПРАВЛЕНО: от 500 до 1000) ---
@router.message(F.text == "💸 Вывод средств")
async def withdraw_start(message: Message):
    user = get_user(message.from_user.id)
    if user['balance_stars'] < 500:
        return await message.answer("❌ Минимальная сумма вывода: 500 ⭐. Накопи больше!")
    
    await message.answer(
        "💸 **ФОРМА ЗАЯВКИ НА ВЫВОД**\n\n"
        "Отправьте сообщение в формате:\n"
        "`СУММА РЕКВИЗИТЫ`\n\n"
        "Пример: `500 TRC20_TXYZ...`\n"
        "⚠️ Допустимая сумма: **от 500 до 1000 ⭐**",
        parse_mode="Markdown"
    )

@router.message(F.chat.type == "private" & ~F.text.startswith("/"))
async def process_withdraw_text(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        return
    
    try:
        amount = int(parts[0])
        details = parts[1]
        user = get_user(message.from_user.id)
        
        # ПРОВЕРКА ЛИМИТОВ 500 - 1000
        if amount < 500 or amount > 1000:
            return await message.answer("❌ Сумма вывода должна быть строго от 500 до 1000 ⭐")
            
        if user['balance_stars'] < amount:
            return await message.answer("❌ Недостаточно средств")
            
        update_balance(message.from_user.id, -amount)
        add_withdrawal(message.from_user.id, amount, details)
        
        await message.answer("✅ Заявка принята! Ожидайте обработки администратором.")
        
        notif = (
            f"🚨 **НОВАЯ ЗАЯВКА НА ВЫВОД**\n"
            f"👤 ID: `{message.from_user.id}`\n"
            f"📝 Имя: {message.from_user.first_name}\n"
            f"💰 Сумма: `{amount}` ⭐\n"
            f"💳 Реквизиты: `{details}`"
        )
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, notif, parse_mode="Markdown")
            except:
                pass
    except ValueError:
        pass

# --- СИНХРОНИЗАЦИЯ С САЙТОМ (WEBAPP) ---
@router.message(Command("play"))
@router.message(F.text == "🎮 ИГРАТЬ")
async def open_game_with_balance(message: Message):
    """Открывает сайт с передачей баланса"""
    user = get_user(message.from_user.id)
    balance = user['balance_stars']
    
    # ИСПРАВЛЕНО: используем GAME_URL вместо GAME_IRL
    game_url_with_balance = f"{GAME_URL}?balance={balance}&user_id={message.from_user.id}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 ОТКРЫТЬ ИГРУ", web_app=WebAppInfo(url=game_url_with_balance))]
    ])
    
    await message.answer(
        f"💰 Твой баланс: **{balance}** ⭐\n\n"
        f"Нажми кнопку ниже, чтобы играть:",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@router.message(F.web_app_data)
async def web_app_data_handler(message: Message):
    """Получает данные от сайта (выигрыши/проигрыши)"""
    try:
        data = json.loads(message.web_app_data.data)
        action = data.get("action")
        
        if action == "win":
            win_amount = int(data.get("amount", 0))
            if win_amount > 0:
                update_balance(message.from_user.id, win_amount)
                new_bal = get_user(message.from_user.id)['balance_stars']
                await message.answer(f"🎉 Выигрыш зачислен! +{win_amount} ⭐\nНовый баланс: {new_bal} ⭐")
                
        elif action == "lose":
            lose_amount = int(data.get("amount", 0))
            if lose_amount > 0:
                update_balance(message.from_user.id, -lose_amount)
                new_bal = get_user(message.from_user.id)['balance_stars']
                await message.answer(f"💀 Проигрыш: -{lose_amount} ⭐\nНовый баланс: {new_bal} ⭐")
                
        elif action == "update_balance":
            user = get_user(message.from_user.id)
            await message.answer(f"💳 Ваш актуальный баланс: {user['balance_stars']} ⭐")
            
    except Exception as e:
        logger.error(f"Ошибка обработки данных от сайта: {e}")

# --- АДМИНКА ---
@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT SUM(balance_stars) FROM users")
    total_balance = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM withdrawals WHERE status='pending'")
    pending_withdraws = c.fetchone()[0]
    conn.close()
    
    await message.answer(
        f"🛠 **ПАНЕЛЬ АДМИНИСТРАТОРА**\n\n"
        f"👥 Всего пользователей: `{total_users}`\n"
        f"💰 Общий баланс игроков: `{total_balance}` ⭐\n"
        f"🚨 Ожидают вывода: `{pending_withdraws}`\n\n"
        f"**Команды:**\n"
        f"/addbal [ID] [SUMMA] - Начислить звезды\n"
        f"/subbal [ID] [SUMMA] - Снять звезды\n"
        f"/withdraws - Список заявок\n"
        f"/approve [ID_ЗАЯВКИ] - Одобрить вывод\n"
        f"/reject [ID_ЗАЯВКИ] - Отклонить вывод (вернуть деньги)",
        parse_mode="Markdown"
    )

@router.message(Command("addbal"))
async def admin_add_balance(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    parts = message.text.split()
    if len(parts) != 3: return await message.answer("Использование: /addbal USER_ID SUMMA")
    try:
        uid, amt = int(parts[1]), int(parts[2])
        update_balance(uid, amt)
        await message.answer(f"✅ Начислено {amt} ⭐ пользователю {uid}\nНовый баланс: {get_user(uid)['balance_stars']} ⭐")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.message(Command("subbal"))
async def admin_sub_balance(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    parts = message.text.split()
    if len(parts) != 3: return await message.answer("Использование: /subbal USER_ID SUMMA")
    try:
        uid, amt = int(parts[1]), int(parts[2])
        update_balance(uid, -amt)
        await message.answer(f"✅ Снято {amt} ⭐ у пользователя {uid}\nНовый баланс: {get_user(uid)['balance_stars']} ⭐")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.message(Command("withdraws"))
async def admin_view_withdraws(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM withdrawals WHERE status='pending' ORDER BY id DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    if not rows: return await message.answer("✅ Нет новых заявок на вывод.")
    txt = "🚨 **ОЧЕРЕДЬ ВЫВОДА**\n\n" + "\n".join(f"ID: `{r['id']}` | User: `{r['user_id']}` | Sum: `{r['amount']}`\nDetails: `{r['details']}`" for r in rows)
    await message.answer(txt, parse_mode="Markdown")

@router.message(Command("approve"))
async def admin_approve_withdraw(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    parts = message.text.split()
    if len(parts) != 2: return await message.answer("Использование: /approve ID_ЗАЯВКИ")
    try:
        wid = int(parts[1])
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM withdrawals WHERE id = ? AND status='pending'", (wid,))
        w = c.fetchone()
        if not w:
            conn.close()
            return await message.answer("❌ Заявка не найдена или уже обработана")
        c.execute("UPDATE withdrawals SET status='approved' WHERE id=?", (wid,))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Заявка #{wid} одобрена")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.message(Command("reject"))
async def admin_reject_withdraw(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    parts = message.text.split()
    if len(parts) != 2: return await message.answer("Использование: /reject ID_ЗАЯВКИ")
    try:
        wid = int(parts[1])
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM withdrawals WHERE id = ? AND status='pending'", (wid,))
        w = c.fetchone()
        if not w:
            conn.close()
            return await message.answer("❌ Заявка не найдена или уже обработана")
        update_balance(w['user_id'], w['amount'])
        c.execute("UPDATE withdrawals SET status='rejected' WHERE id=?", (wid,))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Заявка #{wid} отклонена. Деньги возвращены пользователю.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

# --- ЗАПУСК ---
async def main():
    init_db()
    dp.include_router(router)
    logger.info("Bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
