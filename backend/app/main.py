from fastapi import FastAPI

from app.routes.tasks import router as tasks_router

app = FastAPI(title="TaskPay API")

app.include_router(tasks_router)


@app.get("/")
def root():
    return {"app": "TaskPay", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}
