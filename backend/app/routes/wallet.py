from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.users import User
from app.models.transactions import Transaction


router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("")
def get_wallet(user_id: int):
    db: Session = next(get_db())

    try:
        user = db.get(User, user_id)

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        balance = db.scalar(
            select(
                func.coalesce(func.sum(Transaction.amount), 0)
            ).where(
                Transaction.user_id == user.id
            )
        ) or 0

        total_earned = db.scalar(
            select(
                func.coalesce(func.sum(Transaction.amount), 0)
            ).where(
                Transaction.user_id == user.id,
                Transaction.amount > 0
            )
        ) or 0

        total_withdrawn = db.scalar(
            select(
                func.coalesce(
                    func.sum(Transaction.amount * -1), 0
                )
            ).where(
                Transaction.user_id == user.id,
                Transaction.amount < 0
            )
        ) or 0

        return {
            "user_id": user.id,
            "available_balance": balance,
            "pending_balance": 0,
            "total_earned": total_earned,
            "total_withdrawn": total_withdrawn,
        }

    finally:
        db.close()
