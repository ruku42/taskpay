from datetime import datetime, timedelta
import secrets
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
        TaskCompletion.verification_status.in_(["pending", "verified"])
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

    reward_paisa = int(task.reward_amount)

    now = datetime.utcnow()
    session_token = secrets.token_urlsafe(32)
    session_expires_at = now + timedelta(minutes=30)

    session_row = db.execute(
        text("""
            INSERT INTO task_sessions
            (
                task_id,
                user_id,
                session_token,
                started_at,
                expires_at,
                status
            )
            VALUES
            (
                :task_id,
                :user_id,
                :session_token,
                :started_at,
                :expires_at,
                'active'
            )
            RETURNING id
        """),
        {
            "task_id": task.id,
            "user_id": user.id,
            "session_token": session_token,
            "started_at": now,
            "expires_at": session_expires_at,
        },
    ).fetchone()

    session_id = session_row[0]

    completion = TaskCompletion(
        session_id=session_id,
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
        "reward": reward_paisa / 100,
        "balance": balance_before / 100,
    }


@router.get("/admin/tasks/pending")
def get_pending_tasks(
    init_data: str = Header(..., alias="X-Telegram-Init-Data"),
    db: Session = Depends(get_db),
):
    telegram_user = verify_telegram_init_data(init_data)

    if not telegram_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid Telegram authentication"
        )

    admin = db.execute(
        text("""
            SELECT id
            FROM admin_users
            WHERE telegram_id = :telegram_id
            AND role = 'super_admin'
            AND status = 'active'
            LIMIT 1
        """),
        {
            "telegram_id": int(telegram_user.get("id"))
        },
    ).fetchone()

    if not admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    rows = db.execute(
        text("""
            SELECT
                tc.id,
                tc.user_id,
                u.telegram_id,
                u.username,
                u.first_name,
                tc.task_id,
                t.title,
                t.task_type,
                t.destination_url,
                tc.reward_amount,
                tc.verification_status,
                tc.created_at
            FROM task_completions tc
            JOIN users u ON u.id = tc.user_id
            JOIN tasks t ON t.id = tc.task_id
            WHERE tc.verification_status = 'pending'
            ORDER BY tc.created_at ASC
        """)
    ).fetchall()

    return [
        {
            "completion_id": row.id,
            "user_id": row.user_id,
            "telegram_id": row.telegram_id,
            "username": row.username,
            "first_name": row.first_name,
            "task_id": row.task_id,
            "title": row.title,
            "task_type": row.task_type,
            "url": row.destination_url,
            "reward": row.reward_amount / 100,
            "status": row.verification_status,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.post("/admin/tasks/{completion_id}/approve")
def approve_task(
    completion_id: int,
    init_data: str = Header(..., alias="X-Telegram-Init-Data"),
    db: Session = Depends(get_db),
):
    telegram_user = verify_telegram_init_data(init_data)

    if not telegram_user:
        raise HTTPException(status_code=401, detail="Invalid Telegram authentication")

    admin = db.execute(
        text("""
            SELECT id
            FROM admin_users
            WHERE telegram_id = :telegram_id
            AND role = 'super_admin'
            AND status = 'active'
            LIMIT 1
        """),
        {"telegram_id": int(telegram_user.get("id"))},
    ).fetchone()

    if not admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    completion = db.query(TaskCompletion).filter(
        TaskCompletion.id == completion_id
    ).first()

    if not completion:
        raise HTTPException(status_code=404, detail="Task completion not found")

    if completion.verification_status != "pending":
        raise HTTPException(status_code=400, detail="Task is not pending")

    balance_before = get_balance(db, completion.user_id)
    reward = int(round(float(completion.reward_amount)))

    completion.verification_status = "verified"
    completion.verified_at = datetime.utcnow()
    completion.rejection_reason = None

    balance_after = balance_before + reward

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
                'task_reward',
                :amount,
                'task_completion',
                :reference_id,
                :balance_before,
                :balance_after,
                :description,
                :created_at
            )
        """),
        {
            "user_id": completion.user_id,
            "amount": reward,
            "reference_id": completion.id,
            "balance_before": balance_before,
            "balance_after": balance_after,
            "description": f"Task #{completion.task_id} reward approved",
            "created_at": datetime.utcnow(),
        },
    )

    db.execute(
        text("""
            INSERT INTO audit_logs
            (
                admin_id,
                action,
                entity_type,
                entity_id,
                old_value,
                new_value,
                created_at
            )
            VALUES
            (
                :admin_id,
                'approve_task',
                'task_completion',
                :entity_id,
                'pending',
                'verified',
                :created_at
            )
        """),
        {
            "admin_id": admin.id,
            "entity_id": completion.id,
            "created_at": datetime.utcnow(),
        },
    )

    db.commit()

    return {
        "success": True,
        "message": "Task approved",
        "reward": reward / 100,
        "balance": balance_after / 100,
    }

@router.post("/admin/deposits/{deposit_id}/approve")
def approve_deposit(
    deposit_id: int,
    init_data: str = Header(..., alias="X-Telegram-Init-Data"),
    db: Session = Depends(get_db),
):
    telegram_user = verify_telegram_init_data(init_data)

    if not telegram_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid Telegram authentication"
        )

    admin = db.execute(
        text("""
            SELECT id
            FROM admin_users
            WHERE telegram_id = :telegram_id
            AND role = 'super_admin'
            AND status = 'active'
            LIMIT 1
        """),
        {"telegram_id": int(telegram_user.get("id"))},
    ).fetchone()

    if not admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    deposit = db.execute(
        text("""
            SELECT
                id,
                user_id,
                plan_id,
                amount,
                transaction_id,
                status
            FROM deposits
            WHERE id = :deposit_id
            LIMIT 1
        """),
        {"deposit_id": deposit_id},
    ).fetchone()

    if not deposit:
        raise HTTPException(
            status_code=404,
            detail="Deposit not found"
        )

    if deposit.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Deposit is not pending"
        )

    now = datetime.utcnow()

    db.execute(
        text("""
            UPDATE deposits
            SET
                status = 'approved',
                verified_at = :verified_at,
                verified_by = :verified_by
            WHERE id = :deposit_id
        """),
        {
            "verified_at": now,
            "verified_by": admin.id,
            "deposit_id": deposit.id,
        },
    )

    db.execute(
        text("""
            UPDATE user_plans
            SET status = 'inactive'
            WHERE user_id = :user_id
            AND status = 'active'
        """),
        {"user_id": deposit.user_id},
    )

    db.execute(
        text("""
            INSERT INTO user_plans
            (
                user_id,
                plan_id,
                deposit_id,
                activated_at,
                expires_at,
                status
            )
            VALUES
            (
                :user_id,
                :plan_id,
                :deposit_id,
                :activated_at,
                NULL,
                'active'
            )
        """),
        {
            "user_id": deposit.user_id,
            "plan_id": deposit.plan_id,
            "deposit_id": deposit.id,
            "activated_at": now,
        },
    )

    db.execute(
        text("""
            INSERT INTO audit_logs
            (
                admin_id,
                action,
                entity_type,
                entity_id,
                old_value,
                new_value,
                created_at
            )
            VALUES
            (
                :admin_id,
                'approve_deposit',
                'deposit',
                :entity_id,
                'pending',
                'approved',
                :created_at
            )
        """),
        {
            "admin_id": admin.id,
            "entity_id": deposit.id,
            "created_at": now,
        },
    )

    db.commit()

    plan = db.execute(
        text("""
            SELECT name, daily_task_limit
            FROM plans
            WHERE id = :plan_id
            LIMIT 1
        """),
        {"plan_id": deposit.plan_id},
    ).fetchone()

    return {
        "success": True,
        "message": "Deposit approved and plan activated",
        "deposit_id": deposit.id,
        "plan": plan.name if plan else None,
        "daily_task_limit": plan.daily_task_limit if plan else None,
        "amount": deposit.amount / 100,
    }


@router.get("/admin/deposits/pending")
def get_pending_deposits(
    init_data: str = Header(..., alias="X-Telegram-Init-Data"),
    db: Session = Depends(get_db),
):
    telegram_user = verify_telegram_init_data(init_data)

    if not telegram_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid Telegram authentication"
        )

    admin = db.execute(
        text("""
            SELECT id
            FROM admin_users
            WHERE telegram_id = :telegram_id
            AND role = 'super_admin'
            AND status = 'active'
            LIMIT 1
        """),
        {"telegram_id": int(telegram_user.get("id"))},
    ).fetchone()

    if not admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    rows = db.execute(
        text("""
            SELECT
                d.id,
                d.user_id,
                u.telegram_id,
                u.username,
                u.first_name,
                d.plan_id,
                p.name AS plan_name,
                d.payment_method,
                d.amount,
                d.transaction_id,
                d.status,
                d.submitted_at
            FROM deposits d
            JOIN users u ON u.id = d.user_id
            JOIN plans p ON p.id = d.plan_id
            WHERE d.status = 'pending'
            ORDER BY d.submitted_at ASC
        """)
    ).fetchall()

    return [
        {
            "deposit_id": row.id,
            "user_id": row.user_id,
            "telegram_id": row.telegram_id,
            "username": row.username,
            "first_name": row.first_name,
            "plan_id": row.plan_id,
            "plan": row.plan_name,
            "payment_method": row.payment_method,
            "amount": row.amount / 100,
            "transaction_id": row.transaction_id,
            "status": row.status,
            "submitted_at": row.submitted_at.isoformat(),
        }
        for row in rows
    ]


@router.post("/deposit")
def create_deposit(
    plan_id: int,
    amount: int,
    transaction_id: str,
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

    plan = db.execute(
        text("""
            SELECT id, name, deposit_amount, status
            FROM plans
            WHERE id = :plan_id
            AND status = 'active'
            LIMIT 1
        """),
        {"plan_id": plan_id},
    ).fetchone()

    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Plan not found"
        )

    if amount != plan.deposit_amount:
        raise HTTPException(
            status_code=400,
            detail="Invalid deposit amount"
        )

    transaction_id = transaction_id.strip()

    if not transaction_id:
        raise HTTPException(
            status_code=400,
            detail="Transaction ID is required"
        )

    duplicate = db.execute(
        text("""
            SELECT id
            FROM deposits
            WHERE transaction_id = :transaction_id
            LIMIT 1
        """),
        {"transaction_id": transaction_id},
    ).fetchone()

    if duplicate:
        raise HTTPException(
            status_code=400,
            detail="Transaction ID already submitted"
        )

    now = datetime.utcnow()

    db.execute(
        text("""
            INSERT INTO deposits
            (
                user_id,
                plan_id,
                payment_method,
                amount,
                transaction_id,
                status,
                submitted_at
            )
            VALUES
            (
                :user_id,
                :plan_id,
                'bkash',
                :amount,
                :transaction_id,
                'pending',
                :submitted_at
            )
        """),
        {
            "user_id": user.id,
            "plan_id": plan.id,
            "amount": amount,
            "transaction_id": transaction_id,
            "submitted_at": now,
        },
    )

    db.commit()

    return {
        "success": True,
        "message": "Deposit submitted successfully",
        "status": "pending",
        "plan": plan.name,
        "amount": amount / 100,
        "payment_method": "bkash",
    }

@router.post("/referral")
def create_referral(
    referral_code: str,
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

    if not referral_code.startswith("TP"):
        raise HTTPException(
            status_code=400,
            detail="Invalid referral code"
        )

    try:
        referrer_telegram_id = int(referral_code[2:])
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid referral code"
        )

    if referrer_telegram_id == user.telegram_id:
        raise HTTPException(
            status_code=400,
            detail="Self referral is not allowed"
        )

    referrer = (
        db.query(User)
        .filter(User.telegram_id == referrer_telegram_id)
        .first()
    )

    if not referrer:
        raise HTTPException(
            status_code=404,
            detail="Referrer not found"
        )

    existing = db.execute(
        text("""
            SELECT id
            FROM referrals
            WHERE referred_user_id = :user_id
            LIMIT 1
        """),
        {"user_id": user.id},
    ).fetchone()

    if existing:
        return {
            "success": True,
            "message": "Referral already registered"
        }

    now = datetime.utcnow()

    db.execute(
        text("""
            INSERT INTO referrals
            (
                referrer_user_id,
                referred_user_id,
                referral_code,
                reward_amount,
                status,
                created_at,
                qualified_at
            )
            VALUES
            (
                :referrer_user_id,
                :referred_user_id,
                :referral_code,
                :reward_amount,
                'pending',
                :created_at,
                NULL
            )
        """),
        {
            "referrer_user_id": referrer.id,
            "referred_user_id": user.id,
            "referral_code": referral_code,
            "reward_amount": 500,
            "created_at": now,
        },
    )

    db.commit()

    return {
        "success": True,
        "message": "Referral registered successfully",
        "status": "pending"
    }
