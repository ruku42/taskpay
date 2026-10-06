from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskStartRequest(BaseModel):
    user_id: int


class TaskSubmitRequest(BaseModel):
    user_id: int
    session_id: int


@router.get("")
def get_tasks():
    return {
        "tasks": [
            {
                "id": 1,
                "title": "Promotional Task 1",
                "description": "Visit the promotional page and complete the instructed action.",
                "task_type": "promotion",
                "destination_url": "https://omg10.com/4/11950217",
                "reward_amount": 2,
                "status": "active"
            }
        ]
    }


@router.post("/{task_id}/start")
def start_task(task_id: int, data: TaskStartRequest):
    if data.user_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    return {
        "task_id": task_id,
        "user_id": data.user_id,
        "session_id": 1,
        "session_token": "demo-session-token",
        "expires_at": (
            datetime.utcnow() + timedelta(minutes=10)
        ).isoformat(),
        "message": "Task started successfully"
    }


@router.post("/{task_id}/submit")
def submit_task(task_id: int, data: TaskSubmitRequest):
    if data.user_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    if data.session_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid session_id")

    return {
        "task_id": task_id,
        "user_id": data.user_id,
        "session_id": data.session_id,
        "verification_status": "pending",
        "reward_amount": 2,
        "message": "Task submitted for verification"
    }
