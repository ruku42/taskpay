from fastapi import APIRouter

router = APIRouter(prefix="/wallet", tags=["wallet"])

@router.get("")
def get_wallet():
    return {
        "available_balance": 0,
        "pending_balance": 0,
        "total_earned": 0,
        "total_withdrawn": 0
    }
