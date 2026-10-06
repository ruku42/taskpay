import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.request import HTTPXRequest


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎉 Welcome to TaskPay!\n\n"
        "TaskPay bot is now online. ✅"
    )


def create_bot():
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    request = HTTPXRequest(
        connect_timeout=30,
        read_timeout=30,
        write_timeout=30,
        pool_timeout=30,
    )

    app = Application.builder().token(token).request(request).build()
    app.add_handler(CommandHandler("start", start))

    return app
