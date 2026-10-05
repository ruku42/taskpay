from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FraudFlag(Base):
    __tablename__ = "fraud_flags"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    risk_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        default="low",
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="open",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    resolved_by: Mapped[int | None] = mapped_column(
        ForeignKey("admin_users.id"),
        nullable=True
    )
