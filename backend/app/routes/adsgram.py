import os
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.users import User
from app.models.transactions import Transaction


router = APIRouter(prefix="/api/adsgram", tags=["AdsGram"])


@router.get("/reward")
def adsgram_reward(
    userid: int,
):
    db: Session = next(get_db())

    try:
        user = db.scalar(
            select(User).where(User.telegram_id == userid)
        )

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        reward_amount = int(
            os.getenv("ADSGRAM_REWARD_AMOUNT", "1")
        )

        if reward_amount <= 0:
            raise HTTPException(
                status_code=500,
                detail="Invalid AdsGram reward amount"
            )

        # Prevent accidental duplicate requests within 30 seconds.
        cutoff = datetime.utcnow() - timedelta(seconds=30)

        recent_reward = db.scalar(
            select(Transaction)
            .where(
                Transaction.user_id == user.id,
                Transaction.type == "adsgram_reward",
                Transaction.created_at >= cutoff,
            )
            .order_by(Transaction.id.desc())
        )

        if recent_reward:
            return {
                "ok": True,
                "message": "Reward already processed recently",
                "user_id": user.id,
                "telegram_id": user.telegram_id,
                "reward": 0,
            }

        current_balance = db.scalar(
            select(
                func.coalesce(func.sum(Transaction.amount), 0)
            ).where(
                Transaction.user_id == user.id
            )
        ) or 0

        new_balance = current_balance + reward_amount

        transaction = Transaction(
            user_id=user.id,
            type="adsgram_reward",
            amount=reward_amount,
            reference_type="adsgram",
            reference_id=None,
            balance_before=current_balance,
            balance_after=new_balance,
            description="AdsGram rewarded ad",
        )

        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        return {
            "ok": True,
            "message": "Reward added successfully",
            "user_id": user.id,
            "telegram_id": user.telegram_id,
            "reward": reward_amount,
            "balance": new_balance,
            "transaction_id": transaction.id,
        }

    finally:
        db.close()
