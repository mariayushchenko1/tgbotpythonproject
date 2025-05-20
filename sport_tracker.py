from telegram import Update, ReplyKeyboardMarkup # библиотека для телеграмма
from telegram.ext import ( # расширенная
    Application,
    MessageHandler,
    filters,
    ContextTypes,
    JobQueue,
    CallbackContext
)
from datetime import datetime, timedelta # для дат (выбор дней недели)
import logging # для логирования
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
    CallbackContext  # для напоминаний
)

# настраиваем логгирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Хдля хранения данных пользователя
user_data = {}



class WorkoutData:
    def __init__(self):
        self.selected_days = []  # выбранные пользователем дни
        self.completed = {}  # для статистики (в формате True\False)
        self.reminder_jobs = []  # список напоминаний


# клавиатура
def get_keyboard(buttons):
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


DAYS_KEYBOARD = get_keyboard([["Пн", "Вт", "Ср"], ["Чт", "Пт", "Сб"], ["Вс", "Готово"]]) # основная
YES_NO_KEYBOARD = get_keyboard([["Да", "Нет"]]) # после вопроса
MAIN_KEYBOARD = get_keyboard([["Назад", "статистика"]]) # после выбора дней


# преобразовываем дни в числа
def day_to_num(day):
    days = {"пн": 0, "вт": 1, "ср": 2, "чт": 3, "пт": 4, "сб": 5, "вс": 6}
    return days.get(day.lower(), 0)


# функция выполняется асинхронно
async def start_workout(update: Update, context: ContextTypes.DEFAULT_TYPE): # вызывается принажатии на кнопку зарядка в ГМ
    user_id = update.effective_user.id # узнаем id пользователя
    user_data[user_id] = WorkoutData() # хранилище его данных

    await update.message.reply_text( # асинхронно. Бот в ответ на соо пользователя присылает соо
        "Выбери дни для зарядки:",
        reply_markup=DAYS_KEYBOARD # ReplyKeyboardMarkup. прикрепляем клавиатуру к соо
    )


# после выбора пользователем дней
async def process_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.lower()

    if text == "готово":
        if not user_data[user_id].selected_days:
            await update.message.reply_text("Выбери хотя бы один день!")
            return # если ничего не выбрано, то возврат, не переходит к напоминаниям

        await update.message.reply_text( # данные о текущем соо + ответтное соо
            f"Ты выбрал тренировки в: {', '.join(user_data[user_id].selected_days)}",
            reply_markup=MAIN_KEYBOARD
        )

        # создаем напоминания
        schedule_reminders(user_id, context)

    elif text in ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]:
        if text not in user_data[user_id].selected_days:
            user_data[user_id].selected_days.append(text)
            await update.message.reply_text(f"Добавлен {text}") # приняли запрос пользователя с днями


# напоминания
def schedule_reminders(user_id: int, context: CallbackContext):
    user = user_data[user_id] # просто ввели перем

    # удаляем старые напоминания с помощью функции
    for job in user.reminder_jobs:
        job.schedule_removal()
    user.reminder_jobs = []

    # создаем новые напоминания с помощью функции
    for day in user.selected_days:
        # напоминание накануне - в 20:00
        job = context.job_queue.run_daily( # метод, который план выполн функции кажд день в опр время
            send_reminder,
            time=datetime.strptime("20:00", "%H:%M").time(), # strptime парсит строку во объект врем
            days=(day_to_num(day),),
            context=user_id # кому отправлять напоминание
        )
        user.reminder_jobs.append(job)


# отправдяем напоминания
async def send_reminder(context: CallbackContext):
    user_id = context.job.context
    await context.bot.send_message(
        user_id,
        "Завтра день зарядки! Приготовься к тренировке!"
    )


# вопрос о выполнении зарядки
async def ask_workout_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ты сделал сегодня зарядку?",
        reply_markup=YES_NO_KEYBOARD
    )


# обрабатываем ответ
async def process_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id # ID пользователя
    today = datetime.now().strftime("%Y-%m-%d") # сегодняшняя дата
    answer = update.message.text.lower() # текст ответа пользователя

    user_data[user_id].completed[today] = (answer == "да") # сохр рез на текушую дату; преобразование да в True

# ответ бота в зависимости от ответа пользователя
    await update.message.reply_text(
        "Так держать!" if answer == "да" else "Завтра получится лучше!",
        reply_markup=MAIN_KEYBOARD
    )


# показ статистики
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data or not user_data[user_id].completed: # проверяем есть ли в словаре данные пользователя
        await update.message.reply_text("У тебя еще нет статистики!")
        return

    user = user_data[user_id]
    total = len(user.completed) # всего отмеченных дней
    done = sum(user.completed.values()) # сделанные трени (True)
    missed = total - done # пропущенные (False)

# само сообщение от бота
    stats = (
        "📊 Твоя статистика:\n"
        f"• Всего дней: {total}\n"
        f"• Выполнено: {done}\n"
        f"• Пропущено: {missed}\n\n"
        "• Продолжай работать!"
    )

    await update.message.reply_text(stats)

# список обработчиков для файла ГМ
def get_handlers():
    return [
        MessageHandler(filters.Text(["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс", "Готово"]), process_days), # клав выбор дней
        MessageHandler(filters.Text(["Да", "Нет"]), process_answer), # ответ на вопрос
        MessageHandler(filters.Text(["статистика"]), show_stats), # статистиика
    ]
