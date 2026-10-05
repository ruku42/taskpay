from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/deposit", tags=["deposit"])


class DepositRequest(BaseModel):
    user_id: int
    plan_id: int
    amount: int
    payment_method: str
    transaction_id: str


@router.post("")
def create_deposit(data: DepositRequest):
    return {
        "message": "Deposit submitted for verification",
        "user_id": data.user_id,
        "plan_id": data.plan_id,
        "amount": data.amount,
        "payment_method": data.payment_method,
        "transaction_id": data.transaction_id,
        "status": "pending",
        "payment_number": "01319167792"
    }


@router.get("/info")
def deposit_info():
    return {
        "bkash": "01319167792",
        "nagad": "Coming Soon",
        "minimum_deposit": 100
    }
