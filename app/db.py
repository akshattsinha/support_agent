from datetime import datetime

from sqlalchemy import (
    create_engine,
    String,
    Text,
    DateTime,
    JSON,
    Boolean,
    Float,
    Integer,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
)

from app.config import settings


engine = create_engine(
    settings.database_url,
    connect_args=(
        {"check_same_thread": False}
        if settings.database_url.startswith("sqlite")
        else {}
    ),
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


class TicketRow(Base):
    __tablename__ = "tickets"

    ticket_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )

    customer_name: Mapped[str] = mapped_column(String)
    subject: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)

    category: Mapped[str] = mapped_column(
        String,
        default="Other",
    )

    severity: Mapped[str] = mapped_column(
        String,
        default="LOW",
    )

    confidence: Mapped[float] = mapped_column(
        default=0.0,
    )

    status: Mapped[str] = mapped_column(
        String,
        default="NEW",
    )

    team: Mapped[str] = mapped_column(
        String,
        default="General Support",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


class AnalysisRow(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    ticket_id: Mapped[str] = mapped_column(
        String,
        index=True,
    )

    data: Mapped[dict] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


class AuditRow(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    ticket_id: Mapped[str] = mapped_column(
        String,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(String)
    actor: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)

    metadata_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


class FeedbackRow(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    ticket_id: Mapped[str] = mapped_column(
        String,
        index=True,
    )

    analyst: Mapped[str] = mapped_column(
        String,
        default="analyst",
    )

    ai_category: Mapped[str] = mapped_column(String)
    human_category: Mapped[str] = mapped_column(String)

    ai_severity: Mapped[str] = mapped_column(String)
    human_severity: Mapped[str] = mapped_column(String)

    ai_escalate: Mapped[bool] = mapped_column(Boolean)
    human_escalate: Mapped[bool] = mapped_column(Boolean)

    reason: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


class LearningExampleRow(Base):
    __tablename__ = "learning_examples"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    ticket_id: Mapped[str] = mapped_column(
        String,
        index=True,
    )

    input_text: Mapped[str] = mapped_column(Text)
    corrected_output: Mapped[dict] = mapped_column(JSON)

    reason: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    source_feedback_id: Mapped[int] = mapped_column(
        Integer,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


class LearningRunRow(Base):
    __tablename__ = "learning_runs"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    feedback_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    corrections: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    agreement_rate: Mapped[float] = mapped_column(
        Float,
        default=0.0,
    )

    status: Mapped[str] = mapped_column(
        String,
        default="COMPLETED",
    )

    summary: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


# ============================================================
# HUMAN SUPPORT CHAT
# ============================================================

class SupportMessageRow(Base):
    __tablename__ = "support_messages"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    ticket_id: Mapped[str] = mapped_column(
        String,
        index=True,
    )

    sender: Mapped[str] = mapped_column(
        String,
        default="support_agent",
    )

    message: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

Base.metadata.create_all(engine)


# ============================================================
# AUDIT LOG
# ============================================================

def log_event(
    ticket_id,
    event_type,
    actor,
    description,
    metadata=None,
):
    with SessionLocal() as db:
        db.add(
            AuditRow(
                ticket_id=ticket_id,
                event_type=event_type,
                actor=actor,
                description=description,
                metadata_json=metadata or {},
            )
        )

        db.commit()