from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    destination_url: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    reward_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    daily_limit: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )

    cooldown_seconds: Mapped[int] = mapped_column(
        Integer,
        default=60,
        nullable=False
    )

    verification_type: Mapped[str] = mapped_column(
        String(50),
        default="manual",
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False
    )

    start_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    end_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
