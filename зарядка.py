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
import logging # для логирования (отслеживания действий и их "запоминания")
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

# Хдля хранения данных, которые пользователь нам оставит
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
MAIN_KEYBOARD = get_keyboard([["Назад", "Статистика"]]) # после выбора дней


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
    user_id = update.effective_user.id
    today = datetime.now().strftime("%Y-%m-%d")
    answer = update.message.text.lower()

    user_data[user_id].completed[today] = (answer == "да")

    await update.message.reply_text(
        "✅ Отлично! Так держать!" if answer == "да" else "😊 Завтра получится лучше!",
        reply_markup=MAIN_KEYBOARD
    )


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику"""
    user_id = update.effective_user.id
    if user_id not in user_data or not user_data[user_id].completed:
        await update.message.reply_text("У тебя еще нет статистики!")
        return

    user = user_data[user_id]
    total = len(user.completed)
    done = sum(user.completed.values())
    missed = total - done

    stats = (
        "📊 Твоя статистика:\n"
        f"• Всего дней: {total}\n"
        f"• Выполнено: {done}\n"
        f"• Пропущено: {missed}\n\n"
        f"{'🔥 Идеально!' if done == total else '💪 Продолжай работать!'}"
    )

    await update.message.reply_text(stats)


def get_handlers():
    """Возвращает обработчики для главного файла"""
    return [
        MessageHandler(filters.Text(["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс", "Готово"]), process_days),
        MessageHandler(filters.Text(["Да", "Нет"]), process_answer),
        MessageHandler(filters.Text(["Статистика"]), show_stats),
    ]


async def test_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестовая команда для проверки напоминаний"""
    user_id = update.effective_user.id
    # Создаем искусственный контекст для напоминания
    fake_context = CallbackContext.from_update(update, context)
    fake_context.job.context = user_id  # Устанавливаем user_id для контекста
    await send_reminder(fake_context)
    await update.message.reply_text("✅ Тестовое напоминание отправлено!")

