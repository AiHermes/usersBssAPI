import os
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 👇 твой миниапп
WEB_APP_URL = "https://bssdebugv1.flutterflow.app/"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(
            text="🚀 Войти через Telegram",
            web_app=WebAppInfo(url=WEB_APP_URL)
        )]
    ]
    await update.message.reply_text(
        "Нажми кнопку ниже, чтобы запустить Mini App:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    print("✅ Бот запущен. Напиши /start в Telegram.")
    app.run_polling()
