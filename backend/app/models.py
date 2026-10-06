from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=False)

    balance = Column(Float, default=0.0)
    referral_count = Column(Integer, default=0)
    valid_referrals = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    task_type = Column(String, nullable=False)
    url = Column(String, nullable=False)

    reward = Column(Float, default=0.50)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class TaskCompletion(Base):
    __tablename__ = "task_completions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, nullable=False)
    task_id = Column(Integer, nullable=False)

    reward = Column(Float, default=0.50)

    completed_at = Column(DateTime, default=datetime.utcnow)


class Deposit(Base):
    __tablename__ = "deposits"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, nullable=False)

    amount = Column(Float, nullable=False)
    transaction_id = Column(String, nullable=False)

    status = Column(String, default="pending")

    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, nullable=False)

    amount = Column(Float, nullable=False)
    method = Column(String, default="bkash")
    account_number = Column(String, nullable=False)

    status = Column(String, default="pending")

    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)


class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)

    referrer_id = Column(Integer, nullable=False)
    referred_user_id = Column(Integer, nullable=False)

    referrer_bonus = Column(Float, default=5.0)
    referred_bonus = Column(Float, default=5.0)

    status = Column(String, default="pending")

    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
