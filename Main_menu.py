from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from зарядка import start_workout, get_handlers
from mood_tracker import setup as setup_mood_tracker
from sleep_tracker import setup as setup_sleep_tracker


# создаем сами кнопки
START_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["Зарядка", "Трекер сна"],
        ["Трекер настроения", "Водный баланс"],
        ["Трекер приема таблеток"]
    ],
    resize_keyboard=True
)

# подменю (тут пока только кнопка назад)
CHARGE_KEYBOARD = ReplyKeyboardMarkup([["Назад"]], resize_keyboard=True)
SLEEP_KEYBOARD = ReplyKeyboardMarkup([["Назад"]], resize_keyboard=True)
MOOD_KEYBOARD = ReplyKeyboardMarkup([["Назад"]], resize_keyboard=True)
WATER_KEYBOARD = ReplyKeyboardMarkup([["Назад"]], resize_keyboard=True)
PILLS_KEYBOARD = ReplyKeyboardMarkup([["Назад"]], resize_keyboard=True)

# это чтобы клавиатура не сьезжала


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите раздел:",
        reply_markup=START_KEYBOARD
    )
# главный экран в самом начале


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
# далее кнопки, которые мы выбираем

    if text == "Зарядка":
        await start_workout(update, context)


    elif text == "Трекер сна":
        await update.message.reply_text(
            "Вы в трекере сна",
            reply_markup=SLEEP_KEYBOARD
        )
    elif text == "Трекер настроения":
        await update.message.reply_text(
            "Вы в трекере настроения",
            reply_markup=MOOD_KEYBOARD
        )
    elif text == "Водный баланс":
        await update.message.reply_text(
            "Вы в разделе водного баланса",
            reply_markup=WATER_KEYBOARD
        )
    elif text == "Трекер приема таблеток":
        await update.message.reply_text(
            "Вы в трекере приема таблеток",
            reply_markup=PILLS_KEYBOARD
        )
    elif text == "Назад":
        await start(update, context)



def main():
    load_dotenv()
    TOKEN = os.getenv("BOT_TOKEN")
    application = Application.builder().token(TOKEN).build()

    application.add_handlers(get_handlers())

    setup_mood_tracker(application)
    setup_sleep_tracker(application)
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))

    application.run_polling()



if __name__ == "__main__":
    main()


