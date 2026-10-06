from sqlalchemy import Column, Integer, BigInteger, String, Float, Boolean, DateTime
from datetime import datetime

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)

    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)

    status = Column(String(20), nullable=False)
    is_channel_verified = Column(Boolean, nullable=False)
    welcome_bonus_claimed = Column(Boolean, nullable=False)

    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    last_seen_at = Column(DateTime, nullable=True)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)
    description = Column(String, nullable=True)

    task_type = Column(String, nullable=False)
    destination_url = Column(String, nullable=False)

    reward_amount = Column(Integer, default=50)

    daily_limit = Column(Integer, default=1)
    cooldown_seconds = Column(Integer, default=0)

    verification_type = Column(String, default="manual")

    status = Column(String, default="active")

    start_at = Column(DateTime, nullable=True)
    end_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


class TaskCompletion(Base):
    __tablename__ = "task_completions"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(Integer, nullable=True)
    task_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)

    reward_amount = Column(Integer, default=50)

    verification_status = Column(String, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)

    created_at = Column(DateTime, nullable=False)
