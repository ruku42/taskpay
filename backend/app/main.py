import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from telegram import Update

from app.bot import create_bot
from app.routes import router


WEB_APP_FILE = Path(__file__).resolve().parents[2] / "frontend" / "index.html"


@asynccontextmanager
async def lifespan(app):
    telegram_bot = create_bot()

    await telegram_bot.initialize()
    await telegram_bot.start()

    webhook_url = os.getenv(
        "WEBHOOK_URL",
        "https://taskpay-vs27.onrender.com/telegram/webhook"
    )

    await telegram_bot.bot.set_webhook(webhook_url)

    app.state.telegram_bot = telegram_bot

    yield

    await telegram_bot.bot.delete_webhook()
    await telegram_bot.stop()
    await telegram_bot.shutdown()


app = FastAPI(
    title="TaskPay API",
    lifespan=lifespan
)

app.include_router(router)


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    update = Update.de_json(
        data,
        app.state.telegram_bot.bot
    )

    await app.state.telegram_bot.process_update(update)

    return {"ok": True}


@app.get("/")
def root():
    return {
        "app": "TaskPay",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.get("/app")
def mini_app():
    return FileResponse(WEB_APP_FILE)
