"""
ORM models for NoCap.

Three core tables are stubbed out here — columns and relationships will be
fleshed out in future tasks:

  Capture  – a single recorded media item uploaded by a user.
  Report   – a moderation/analysis report attached to a Capture.
  Ledger   – an immutable audit log of significant backend events.

All models inherit from Base (defined in cloud.database) so that
`Base.metadata.create_all(engine)` can build the schema in one call.
"""

import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from cloud.database import Base


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------
class Capture(Base):
    """Represents a media file uploaded by a user."""

    __tablename__ = "captures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # One capture may have many reports.
    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="capture", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Capture id={self.id} user_id={self.user_id!r} status={self.status!r}>"


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
class Report(Base):
    """Moderation or analysis report for a Capture."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    capture_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("captures.id"), nullable=False, index=True
    )
    report_type: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    capture: Mapped["Capture"] = relationship("Capture", back_populates="reports")

    def __repr__(self) -> str:
        return f"<Report id={self.id} capture_id={self.capture_id} type={self.report_type!r}>"


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------
class Ledger(Base):
    """Append-only audit log entry."""

    __tablename__ = "ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<Ledger id={self.id} actor={self.actor!r} action={self.action!r}>"
        )
