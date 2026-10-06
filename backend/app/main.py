import os

from fastapi import FastAPI, Request
from telegram import Update
from app.bot import create_bot

app = FastAPI(title="TaskPay API")

telegram_bot = create_bot()


@app.on_event("startup")
async def startup():
    await telegram_bot.initialize()
    await telegram_bot.start()

    webhook_url = os.getenv(
        "WEBHOOK_URL",
        "https://taskpay-vs27.onrender.com/telegram/webhook"
    )

    await telegram_bot.bot.set_webhook(webhook_url)


@app.on_event("shutdown")
async def shutdown():
    await telegram_bot.bot.delete_webhook()
    await telegram_bot.stop()
    await telegram_bot.shutdown()


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    update = Update.de_json(data, telegram_bot.bot)

    await telegram_bot.process_update(update)

    return {"ok": True}


@app.get("/")
def root():
    return {"app": "TaskPay", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}
