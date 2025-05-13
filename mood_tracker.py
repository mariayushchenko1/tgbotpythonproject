from telegram import Update, ReplyKeyboardMarkup # базовые классы telegram API
from telegram.ext import (
    Application, # основной класс приложения бота
    MessageHandler, # обработчик сообщений
    filters, # фильтры для обработки сообщений
    ContextTypes, # типы контекста
    CallbackContext # контекст обратного вызова
)
import sqlite3 #БД

# файл базы данных
DB_NAME = "mood.db"

# клавиатура для оценки настроения
main_kb = ReplyKeyboardMarkup(
    [["1", "2", "3"], ["4", "5", "Статистика"], ["Назад"]],
    resize_keyboard=True
)

# клавиатура для выбора фактора влияния
factor_kb = ReplyKeyboardMarkup(
    [["Друзья", "Семья"], ["Работа", "Учеба"], ["Здоровье", "Другое"], ["Назад"]],
    resize_keyboard=True
)

# функции работы с базой данных
# инициализация базы данных и создание таблицы для хранения данных
def init_db():
    conn = sqlite3.connect(DB_NAME) # подключение к БД
    cursor = conn.cursor() # создание курсора
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS moods (
            user_id INTEGER,
            rating INTEGER,
            factor TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit() # сохранение изменений
    conn.close() # закрытие соединения

# основные функции бота
# обработка начала работы с трекером настроения
# отправление пользователю клавиатуры для оценки настроения
async def start_mood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Оцените настроение:", reply_markup=main_kb)

# обработка выбранной пользователем оценки
async def process_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # обработка кнопки "Статистика"
    if text == "Статистика":
        return await show_stats(update, context) # Переход к показу статистики
    # обработка кнопки "Назад"
    if text == "Назад":
        return await start(update, context) # Возврат в начало

    if text in ["1", "2", "3", "4", "5"]:
        context.user_data['rating'] = int(text) # сохранение оценки в контексте
        await update.message.reply_text("Что повлияло?", reply_markup=factor_kb) # подключение клавиатуры факторов

# обработка выбранного фактора и сохранение в БД
async def process_factor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Назад":
        return await start_mood(update, context)

# проверка наличия оценки в контексте
    if 'rating' not in context.user_data:
        return await update.message.reply_text("Пожалуйста, начните сначала", reply_markup=main_kb)

# получение данных для сохранения
    user_id = update.effective_user.id # id пользователя
    rating = context.user_data['rating'] # оценка настроения
    factor = text # фактор

# сохранение в базу данных
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO moods (user_id, rating, factor) VALUES (?, ?, ?)",
        (user_id, rating, factor)
    )
    conn.commit() # сохранение изменений
    conn.close() # закрытие соединения

# отправка подтверждения пользователю
    await update.message.reply_text(
        f"✅ Сохранено! Настроение: {rating}",
        reply_markup=main_kb
    )
    context.user_data.clear() # очистка временных данных

# статистика
async def show_stats(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

# подключение к БД
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

# получение средней оценки
    cursor.execute("SELECT AVG(rating) FROM moods WHERE user_id = ?", (user_id,))
    avg = cursor.fetchone()[0]

# получение самого частого фактора
    cursor.execute("""
        SELECT factor, COUNT(*) as count 
        FROM moods 
        WHERE user_id = ? 
        GROUP BY factor 
        ORDER BY count DESC 
        LIMIT 1
    """, (user_id,))
    result = cursor.fetchone()
    conn.close() # закрытие соединения

# формирование и отправка статистики
    if avg is None:
        await update.message.reply_text("У вас пока нет сохраненных данных", reply_markup=main_kb)
    else:
        message = (
            "📊 Ваша статистика:\n"
            f"• Средний балл: {round(avg, 2)}\n"
            f"• Самый частый фактор: {result[0] if result else 'нет данных'}"
        )
        await update.message.reply_text(message, reply_markup=main_kb)

# настройка и запуск бота
def setup(application):
    init_db() # инициализация базы данных
    # регистрация обработчиков сообщений
    application.add_handler(MessageHandler(filters.Regex("^Трекер настроения$"), start_mood))
    application.add_handler(MessageHandler(filters.Regex("^([1-5]|Статистика)$"), process_rating))
    application.add_handler(
        MessageHandler(filters.Regex("^(Друзья|Семья|Работа|Учеба|Здоровье|Другое)$"), process_factor))