from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.bot import create_bot
from app.routes.tasks import router as tasks_router
from app.routes.wallet import router as wallet_router
from app.routes.deposits import router as deposits_router


@asynccontextmanager
async def lifespan(app):
    telegram_bot = create_bot()
    await telegram_bot.initialize()
    await telegram_bot.start()
    await telegram_bot.updater.start_polling()

    yield

    await telegram_bot.updater.stop()
    await telegram_bot.stop()
    await telegram_bot.shutdown()


app = FastAPI(title="TaskPay API", lifespan=lifespan)

app.include_router(tasks_router)
app.include_router(wallet_router)
app.include_router(deposits_router)


@app.get("/")
def root():
    return {"app": "TaskPay", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}
