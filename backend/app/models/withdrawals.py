from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Withdrawal(Base):
    __tablename__ = "withdrawals"

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

    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    payment_method: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    account_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False
    )

    risk_status: Mapped[str] = mapped_column(
        String(20),
        default="normal",
        nullable=False
    )

    requested_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    processed_by: Mapped[int | None] = mapped_column(
        ForeignKey("admin_users.id"),
        nullable=True
    )

    payment_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    rejection_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )
