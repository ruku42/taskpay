from fastapi import FastAPI

from app.models import (
    User,
    Plan,
    UserPlan,
    AdminUser,
    Deposit,
    Task,
    TaskSession,
    TaskCompletion,
    Transaction,
    Withdrawal,
    Referral,
    Bonus,
    FraudFlag,
    AuditLog,
    Setting,
    Announcement,
)

app = FastAPI(title="TaskPay API")


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
