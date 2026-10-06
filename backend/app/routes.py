from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Task, TaskCompletion
from app.auth import verify_telegram_init_data


router = APIRouter(
    prefix="/api",
    tags=["tasks"]
)


@router.get("/tasks")
def get_tasks(db: Session = Depends(get_db)):
    tasks = (
        db.query(Task)
        .filter(Task.status == "active")
        .all()
    )

    return [
        {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "task_type": task.task_type,
            "url": task.destination_url,
            "reward": task.reward_amount,
        }
        for task in tasks
    ]


@router.post("/tasks/{task_id}/complete")
def complete_task(
    task_id: int,
    init_data: str = Header(..., alias="X-Telegram-Init-Data"),
    db: Session = Depends(get_db),
):
    telegram_user = verify_telegram_init_data(init_data)

    if not telegram_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid Telegram authentication"
        )

    telegram_id = str(telegram_user.get("id"))

    if not telegram_id:
        raise HTTPException(
            status_code=401,
            detail="Telegram user not found"
        )

    user = (
        db.query(User)
        .filter(User.telegram_id == telegram_id)
        .first()
    )

    if not user:
        user = User(
            telegram_id=telegram_id
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    task = (
        db.query(Task)
        .filter(
            Task.id == task_id,
            Task.status == "active"
        )
        .first()
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    already_completed = (
        db.query(TaskCompletion)
        .filter(
            TaskCompletion.user_id == user.id,
            TaskCompletion.task_id == task.id
        )
        .first()
    )

    if already_completed:
        raise HTTPException(
            status_code=400,
            detail="Task already completed"
        )

    completion = TaskCompletion(
        user_id=user.id,
        task_id=task.id,
        reward=task.reward_amount,
    )

    user.balance += task.reward_amount

    db.add(completion)
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": "Task completed",
        "reward": task.reward_amount,
        "balance": user.balance,
    }
