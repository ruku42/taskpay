import os
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.request import HTTPXRequest

from app.database import get_db
from app.models.users import User


WEB_APP_URL = "https://taskpay-vs27.onrender.com/app"
ADMIN_WEB_APP_URL = "https://taskpay-vs27.onrender.com/admin"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user = update.effective_user

    if not telegram_user:
        return

    db = next(get_db())

    try:
        user = db.query(User).filter(
            User.telegram_id == telegram_user.id
        ).first()

        if not user:
            user = User(
                telegram_id=telegram_user.id,
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
                status="active",
                last_seen_at=datetime.utcnow(),
            )

            db.add(user)

        else:
            user.username = telegram_user.username
            user.first_name = telegram_user.first_name
            user.last_name = telegram_user.last_name
            user.last_seen_at = datetime.utcnow()

        db.commit()

    finally:
        db.close()

    keyboard = [
        [
            InlineKeyboardButton(
                "🚀 Open TaskPay",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        ],
        [
            InlineKeyboardButton(
                "🛡️ Admin Panel",
                web_app=WebAppInfo(url=ADMIN_WEB_APP_URL)
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎉 Welcome to TaskPay!\n\n"
        "💰 Earn rewards by completing tasks.\n"
        "👇 Tap the button below to open TaskPay.",
        reply_markup=reply_markup
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
