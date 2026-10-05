from datetime import datetime, timedelta
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.tasks import Task
from app.models.task_sessions import TaskSession
from app.models.task_completions import TaskCompletion

router = APIRouter(prefix="/tasks", tags=["Tasks"])


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


@router.post("/{task_id}/start")
def start_task(
    task_id: int,
    user_id: int,
    db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)

    if not task or task.status != "active":
        raise HTTPException(status_code=404, detail="Task not found")

    token = secrets.token_urlsafe(32)
    now = datetime.utcnow()

    session = TaskSession(
        task_id=task.id,
        user_id=user_id,
        session_token=token,
        started_at=now,
        expires_at=now + timedelta(minutes=10),
        status="started",
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "session_token": session.session_token,
        "task_id": task.id,
        "destination_url": task.destination_url,
        "expires_at": session.expires_at,
    }


@router.post("/{task_id}/submit")
def submit_task(
    task_id: int,
    session_id: int,
    user_id: int,
    db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)
    session = db.get(TaskSession, session_id)

    if not task or not session:
        raise HTTPException(status_code=404, detail="Task session not found")

    if session.task_id != task_id or session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Invalid task session")

    if session.status != "started":
        raise HTTPException(status_code=400, detail="Task session already used")

    if session.expires_at < datetime.utcnow():
        session.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="Task session expired")

    completion = TaskCompletion(
        session_id=session.id,
        task_id=task.id,
        user_id=user_id,
        reward_amount=task.reward_amount,
        verification_status="pending",
    )

    session.status = "submitted"

    db.add(completion)
    db.commit()
    db.refresh(completion)

    return {
        "message": "Task submitted for verification",
        "completion_id": completion.id,
        "reward_amount": task.reward_amount,
        "verification_status": "pending",
    }
