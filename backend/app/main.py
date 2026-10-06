from fastapi import FastAPI

from app.routes.tasks import router as tasks_router
from app.routes.wallet import router as wallet_router
from app.routes.deposits import router as deposits_router

app = FastAPI(title="TaskPay API")

app.include_router(tasks_router)
app.include_router(wallet_router)
app.include_router(deposits_router)


@app.get("/")
def root():
    return {"app": "TaskPay", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}
