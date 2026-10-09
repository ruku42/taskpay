from datetime import datetime, timedelta
import hashlib
import hmac
import json
import os
import secrets
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.tasks import Task
from app.models.task_sessions import TaskSession
from app.models.task_completions import TaskCompletion
from app.models.users import User


router = APIRouter(prefix="/tasks", tags=["Tasks"])


def validate_telegram_init_data(init_data: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not bot_token:
        raise HTTPException(
            status_code=500,
            detail="TELEGRAM_BOT_TOKEN is not configured"
        )

    data = dict(parse_qsl(init_data, keep_blank_values=True))

    received_hash = data.pop("hash", None)

    if not received_hash:
        raise HTTPException(
            status_code=401,
            detail="Invalid Telegram init data"
        )

    data_check_string = "\n".join(
        f"{key}={data[key]}"
        for key in sorted(data)
    )

    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode(),
        hashlib.sha256
    ).digest()

    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid Telegram authentication"
        )

    user_data = data.get("user")

    if not user_data:
        raise HTTPException(
            status_code=401,
            detail="Telegram user not found"
        )

    try:
        return json.loads(user_data)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=401,
            detail="Invalid Telegram user data"
        )


@router.get("")
def get_tasks(db: Session = Depends(get_db)):
    tasks = db.scalars(
        select(Task).where(Task.status == "active")
    ).all()

    return [
        {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "task_type": task.task_type,
            "destination_url": task.destination_url,
            "reward_amount": task.reward_amount,
            "daily_limit": task.daily_limit,
            "cooldown_seconds": task.cooldown_seconds,
        }
        for task in tasks
    ]


@router.post("/{task_id}/complete")
def complete_task(
    task_id: int,
    x_telegram_init_data: str | None = Header(
        default=None
    ),
    db: Session = Depends(get_db),
):
    if not x_telegram_init_data:
        raise HTTPException(
            status_code=401,
            detail="Telegram authentication required"
        )

    telegram_user = validate_telegram_init_data(
        x_telegram_init_data
    )

    telegram_id = telegram_user.get("id")

    if not telegram_id:
        raise HTTPException(
            status_code=401,
            detail="Telegram user ID not found"
        )

    user = db.scalar(
        select(User).where(
            User.telegram_id == telegram_id
        )
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="TaskPay user not found. Please open the bot first."
        )

    task = db.get(Task, task_id)

    if not task or task.status != "active":
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    now = datetime.utcnow()

    recent_completion = db.scalar(
        select(TaskCompletion)
        .where(
            TaskCompletion.task_id == task.id,
            TaskCompletion.user_id == user.id,
            TaskCompletion.created_at >= now - timedelta(
                seconds=task.cooldown_seconds
            )
        )
        .order_by(TaskCompletion.id.desc())
    )

    if recent_completion:
        raise HTTPException(
            status_code=429,
            detail="Task cooldown is still active"
        )

    token = secrets.token_urlsafe(32)

    session = TaskSession(
        task_id=task.id,
        user_id=user.id,
        session_token=token,
        started_at=now,
        expires_at=now + timedelta(minutes=10),
        status="submitted",
    )

    db.add(session)
    db.flush()

    completion = TaskCompletion(
        session_id=session.id,
        task_id=task.id,
        user_id=user.id,
        reward_amount=task.reward_amount,
        verification_status="pending",
    )

    db.add(completion)
    db.commit()
    db.refresh(completion)

    return {
        "ok": True,
        "message": "Task submitted for verification",
        "completion_id": completion.id,
        "reward_amount": task.reward_amount,
        "verification_status": "pending",
    }
