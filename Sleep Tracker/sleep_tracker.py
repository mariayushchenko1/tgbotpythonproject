from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
import sqlite3
import datetime
import os
from dotenv import load_dotenv

# глобальные переменные
DB_NAME = "sleep.db"
user_states = {}
SET_MORNING, SET_EVENING = range(2)

# клавиатура главного меню
main_kb = ReplyKeyboardMarkup(
    [["Регистрация сна", "Просмотреть отчёт"], ["Назад"]], resize_keyboard=True
)


# команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в трекер сна!", reply_markup=main_kb
    )


# обработка начала регистрации сна
async def handle_sleep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_states[update.effective_user.id] = {"step": "ask_sleep_time"}
    await update.message.reply_text("Во сколько вы легли спать? (например, 23:45)")


# основной обработчик текстовых сообщений
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if text == "Регистрация сна":
        return await handle_sleep(update, context)
    elif text == "Просмотреть отчёт":
        return await send_report(update, context)
    elif text == "Назад":
        return await start(update, context)

    state = user_states.get(user_id)
    if state:
        if state["step"] == "ask_sleep_time":
            state["sleep_time"] = text
            state["step"] = "ask_wake_time"
            await update.message.reply_text(
                "Во сколько вы проснулись? (например, 07:30)"
            )
        elif state["step"] == "ask_wake_time":
            sleep_time = state["sleep_time"]
            wake_time = text
            log_sleep_start(user_id, sleep_time)
            log_wake_time(user_id, wake_time)
            duration = get_last_sleep_duration(user_id)
            msg = (
                f"Вы спали {round(duration, 2)} ч Ὂ4"
                if duration
                else "Не удалось рассчитать продолжительность сна."
            )
            await update.message.reply_text(msg, reply_markup=main_kb)
            user_states.pop(user_id)
    else:
        await update.message.reply_text(
            "Пожалуйста, выберите действие с клавиатуры.", reply_markup=main_kb
        )


# отправка отчёта о сне
async def send_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = get_last_sleep_duration(user_id)
    yesterday = get_yesterday_sleep_duration(user_id)

    if today is None:
        return await update.message.reply_text(
            "Пока нет данных за сегодня.", reply_markup=main_kb
        )

    diff = ""
    if yesterday is not None:
        delta = round(today - yesterday, 2)
        if delta > 0:
            diff = f" Это на {delta} ч больше, чем вчера!"
        elif delta < 0:
            diff = f" Это на {abs(delta)} ч меньше, чем вчера!"
        else:
            diff = " То же самое, что и вчера!"

    await update.message.reply_text(
        f"Сегодня вы спали {round(today, 2)} ч {diff}", reply_markup=main_kb
    )


# установка времени напоминаний
async def set_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT morning_time, evening_time FROM notification_times WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()

    morning = row[0] if row else "не установлено"
    evening = row[1] if row else "не установлено"

    await update.message.reply_text(
        f"Ваши текущие напоминания:\n"
        f"☀️ Утро: {morning}\n"
        f"🌙 Вечер: {evening}\n\n"
        "Введите время утреннего напоминания (ЧЧ:ММ), или 'пропустить':"
    )
    return SET_MORNING


async def set_morning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data["morning_time"] = None if text.lower() == "пропустить" else text
    await update.message.reply_text(
        "Теперь введите время вечернего напоминания (ЧЧ:ММ), или 'пропустить':"
    )
    return SET_EVENING


async def set_evening(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    morning_time = context.user_data.get("morning_time")
    evening_time = (
        None if update.message.text.lower() == "пропустить" else update.message.text
    )

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO notification_times (user_id, morning_time, evening_time)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET morning_time = excluded.morning_time, evening_time = excluded.evening_time
    """,
        (user_id, morning_time, evening_time),
    )
    conn.commit()
    conn.close()

    schedule_notifications(context.application)
    await update.message.reply_text("\u2705 Напоминания обновлены!")
    return ConversationHandler.END


async def cancel_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Настройка напоминаний отменена.")
    return ConversationHandler.END


# запись времени сна
def log_sleep_start(user_id, sleep_time):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    date = str(datetime.date.today())
    cur.execute(
        "INSERT OR IGNORE INTO sleep_logs (user_id, sleep_time, date) VALUES (?, ?, ?)",
        (user_id, sleep_time, date),
    )
    conn.commit()
    conn.close()


# запись времени пробуждения
def log_wake_time(user_id, wake_time):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    date = str(datetime.date.today())
    cur.execute(
        "UPDATE sleep_logs SET wake_time = ? WHERE user_id = ? AND date = ?",
        (wake_time, user_id, date),
    )
    conn.commit()
    conn.close()


# получение продолжительности сна за сегодня
def get_last_sleep_duration(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    date = str(datetime.date.today())
    cur.execute(
        "SELECT sleep_time, wake_time FROM sleep_logs WHERE user_id = ? AND date = ?",
        (user_id, date),
    )
    row = cur.fetchone()
    conn.close()

    if row and row[0] and row[1]:
        fmt = "%H:%M"
        try:
            sleep = datetime.datetime.strptime(row[0], fmt)
            wake = datetime.datetime.strptime(row[1], fmt)
            if wake < sleep:
                wake += datetime.timedelta(days=1)
            duration = (wake - sleep).seconds / 3600
            return duration
        except:
            return None
    return None


# получение продолжительности сна за вчера
def get_yesterday_sleep_duration(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    yesterday = str(datetime.date.today() - datetime.timedelta(days=1))
    cur.execute(
        "SELECT sleep_time, wake_time FROM sleep_logs WHERE user_id = ? AND date = ?",
        (user_id, yesterday),
    )
    row = cur.fetchone()
    conn.close()

    if row and row[0] and row[1]:
        fmt = "%H:%M"
        try:
            sleep = datetime.datetime.strptime(row[0], fmt)
            wake = datetime.datetime.strptime(row[1], fmt)
            if wake < sleep:
                wake += datetime.timedelta(days=1)
            duration = (wake - sleep).seconds / 3600
            return duration
        except:
            return None
    return None


# заглушка — реализация напоминаний по времени (опционально)
def schedule_notifications(app):
    pass


# создание таблиц в базе данных
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sleep_logs (
            user_id INTEGER,
            sleep_time TEXT,
            wake_time TEXT,
            date TEXT
        )
    """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_times (
            user_id INTEGER PRIMARY KEY,
            morning_time TEXT,
            evening_time TEXT
        )
    """
    )
    conn.commit()
    conn.close()

def setup(application):
    init_db()  # инициализация базы данных
    # регистрация обработчиков сообщений
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # для напоминаний
    notification_conv = ConversationHandler(
        entry_points=[CommandHandler("напоминания", set_notifications)],
        states={
            SET_MORNING: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_morning)],
            SET_EVENING: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_evening)],
        },
        fallbacks=[CommandHandler("отмена", cancel_notifications)],
    )
    application.add_handler(notification_conv)
