from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Task, TaskCompletion
from app.auth import verify_telegram_init_data


router = APIRouter(
    prefix="/api",
    tags=["tasks"]
)


def get_or_create_user(db: Session, telegram_user):
    telegram_id = str(telegram_user.get("id"))

    if not telegram_id:
        raise HTTPException(
            status_code=401,
            detail="Telegram user not found"
        )

    user = (
        db.query(User)
        .filter(User.telegram_id == int(telegram_id))
        .first()
    )

    now = datetime.utcnow()

    if not user:
        user = User(
            telegram_id=int(telegram_id),
            username=telegram_user.get("username"),
            first_name=telegram_user.get("first_name"),
            last_name=telegram_user.get("last_name"),
            status="active",
            is_channel_verified=False,
            welcome_bonus_claimed=False,
            created_at=now,
            updated_at=now,
            last_seen_at=now,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


def get_balance(db: Session, user_id: int):
    row = db.execute(
        text("""
            SELECT COALESCE(
                (
                    SELECT balance_after
                    FROM transactions
                    WHERE user_id = :user_id
                    ORDER BY id DESC
                    LIMIT 1
                ),
                0
            )
        """),
        {"user_id": user_id},
    ).scalar()

    return int(row or 0)


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

    user = get_or_create_user(db, telegram_user)

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

    existing = db.query(TaskCompletion).filter(
        TaskCompletion.user_id == user.id,
        TaskCompletion.task_id == task.id,
        TaskCompletion.verification_status.in_(
            ["pending", "verified"]
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Task already submitted"
        )

    verified_count = db.execute(
        text("""
            SELECT COUNT(*)
            FROM task_completions
            WHERE user_id = :user_id
            AND verification_status = 'verified'
        """),
        {"user_id": user.id},
    ).scalar() or 0

    active_plan = db.execute(
        text("""
            SELECT p.id, p.name, p.daily_task_limit, up.expires_at
            FROM user_plans up
            JOIN plans p ON p.id = up.plan_id
            WHERE up.user_id = :user_id
            AND up.status = 'active'
            AND p.status = 'active'
            AND (
                up.expires_at IS NULL
                OR up.expires_at > :now
            )
            ORDER BY p.daily_task_limit DESC
            LIMIT 1
        """),
        {
            "user_id": user.id,
            "now": datetime.utcnow(),
        },
    ).fetchone()

    if not active_plan:
        if verified_count >= 5:
            raise HTTPException(
                status_code=403,
                detail="Free 5 tasks completed. Please activate a plan."
            )
    else:
        daily_limit = active_plan.daily_task_limit

        if daily_limit != -1:
            today_count = db.execute(
                text("""
                    SELECT COUNT(*)
                    FROM task_completions
                    WHERE user_id = :user_id
                    AND verification_status = 'verified'
                    AND date(created_at) = date(:today)
                """),
                {
                    "user_id": user.id,
                    "today": datetime.utcnow(),
                },
            ).scalar() or 0

            if today_count >= daily_limit:
                raise HTTPException(
                    status_code=403,
                    detail="Daily task limit reached."
                )

    reward_paisa = int(round(float(task.reward_amount) * 100))

    completion = TaskCompletion(
        user_id=user.id,
        task_id=task.id,
        reward_amount=reward_paisa,
        verification_status="pending",
        verified_at=None,
        rejection_reason=None,
        created_at=datetime.utcnow(),
    )

    db.add(completion)
    db.flush()

    balance_before = get_balance(db, user.id)

    db.execute(
        text("""
            INSERT INTO transactions
            (
                user_id,
                type,
                amount,
                reference_type,
                reference_id,
                balance_before,
                balance_after,
                description,
                created_at
            )
            VALUES
            (
                :user_id,
                'task_pending',
                0,
                'task_completion',
                :reference_id,
                :balance_before,
                :balance_before,
                :description,
                :created_at
            )
        """),
        {
            "user_id": user.id,
            "reference_id": completion.id,
            "balance_before": balance_before,
            "description": f"Task #{task.id} submitted for verification",
            "created_at": datetime.utcnow(),
        },
    )

    db.commit()

    return {
        "success": True,
        "status": "pending",
        "message": "Task submitted for verification",
        "reward": task.reward_amount,
        "balance": balance_before / 100,
    }
