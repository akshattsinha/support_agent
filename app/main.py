from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.models import Ticket, FeedbackRequest
from app.agent import process_ticket, investigate

from app.db import (
    SessionLocal,
    TicketRow,
    AnalysisRow,
    AuditRow,
    SupportMessageRow,
)

from app.learning import (
    submit_feedback,
    get_learning_stats,
    run_learning_cycle,
)


app = FastAPI(
    title="AI Support Sentinel",
    version="2.2",
)


# ============================================================
# REQUEST MODELS
# ============================================================

class SupportMessageRequest(BaseModel):
    message: str
    agent: str = "support_agent"


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# ============================================================
# PROCESS TICKET
# ============================================================

@app.post("/tickets/process")
def process(t: Ticket):
    try:
        return process_ticket(t)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# ============================================================
# ALL TICKETS
# ============================================================

@app.get("/tickets")
def tickets():

    with SessionLocal() as db:

        rows = (
            db.query(TicketRow)
            .order_by(
                TicketRow.created_at.desc()
            )
            .all()
        )

        return [
            {
                "ticket_id": r.ticket_id,
                "customer_name": r.customer_name,
                "subject": r.subject,
                "message": r.message,
                "category": r.category,
                "severity": r.severity,
                "confidence": r.confidence,
                "status": r.status,
                "team": r.team,
                "created_at": r.created_at,
            }
            for r in rows
        ]


# ============================================================
# HUMAN ESCALATION QUEUE
#
# IMPORTANT:
# This MUST appear before /tickets/{ticket_id}
# ============================================================

@app.get("/tickets/escalated")
def escalated_tickets():

    with SessionLocal() as db:

        rows = (
            db.query(TicketRow)
            .filter(
                TicketRow.status.in_(
                    [
                        "ESCALATED",
                        "HUMAN_ACTIVE",
                    ]
                )
            )
            .order_by(
                TicketRow.created_at.desc()
            )
            .all()
        )

        return [
            {
                "ticket_id": r.ticket_id,
                "customer_name": r.customer_name,
                "subject": r.subject,
                "message": r.message,
                "category": r.category,
                "severity": r.severity,
                "confidence": r.confidence,
                "status": r.status,
                "team": r.team,
                "created_at": r.created_at,
            }
            for r in rows
        ]


# ============================================================
# TICKET DETAILS
# ============================================================

@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):

    with SessionLocal() as db:

        ticket = (
            db.query(TicketRow)
            .filter_by(
                ticket_id=ticket_id
            )
            .first()
        )

        if not ticket:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found",
            )

        analysis = (
            db.query(AnalysisRow)
            .filter_by(
                ticket_id=ticket_id
            )
            .order_by(
                AnalysisRow.created_at.desc()
            )
            .first()
        )

        events = (
            db.query(AuditRow)
            .filter_by(
                ticket_id=ticket_id
            )
            .order_by(
                AuditRow.timestamp.asc()
            )
            .all()
        )

        return {
            "ticket": {
                "ticket_id": ticket.ticket_id,
                "customer_name": ticket.customer_name,
                "subject": ticket.subject,
                "message": ticket.message,
                "category": ticket.category,
                "severity": ticket.severity,
                "confidence": ticket.confidence,
                "status": ticket.status,
                "team": ticket.team,
                "created_at": ticket.created_at,
            },

            "analysis": (
                analysis.data
                if analysis
                else None
            ),

            "audit": [
                {
                    "event_type": e.event_type,
                    "actor": e.actor,
                    "description": e.description,
                    "metadata": e.metadata_json,
                    "timestamp": e.timestamp,
                }
                for e in events
            ],
        }


# ============================================================
# GET SUPPORT CHAT
# ============================================================

@app.get("/tickets/{ticket_id}/messages")
def get_support_messages(ticket_id: str):

    with SessionLocal() as db:

        ticket = (
            db.query(TicketRow)
            .filter_by(
                ticket_id=ticket_id
            )
            .first()
        )

        if not ticket:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found",
            )

        rows = (
            db.query(SupportMessageRow)
            .filter_by(
                ticket_id=ticket_id
            )
            .order_by(
                SupportMessageRow.created_at.asc()
            )
            .all()
        )

        messages = [
            {
                "id": row.id,
                "ticket_id": row.ticket_id,
                "sender": row.sender,
                "message": row.message,
                "created_at": row.created_at,
            }
            for row in rows
        ]

        # Show the original ticket as the
        # first customer message.
        if not messages:

            messages.append(
                {
                    "id": 0,
                    "ticket_id": ticket.ticket_id,
                    "sender": "customer",
                    "message": ticket.message,
                    "created_at": ticket.created_at,
                }
            )

        return messages


# ============================================================
# SEND SUPPORT MESSAGE
# ============================================================

@app.post("/tickets/{ticket_id}/messages")
def send_support_message(
    ticket_id: str,
    body: SupportMessageRequest,
):

    message = body.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    agent = (
        body.agent.strip()
        or "support_agent"
    )

    with SessionLocal() as db:

        ticket = (
            db.query(TicketRow)
            .filter_by(
                ticket_id=ticket_id
            )
            .first()
        )

        if not ticket:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found",
            )

        if ticket.status == "DONE":
            raise HTTPException(
                status_code=400,
                detail="This ticket has already been closed.",
            )

        # First human response means the agent
        # has taken ownership of the ticket.
        if ticket.status == "ESCALATED":
            ticket.status = "HUMAN_ACTIVE"

        support_message = SupportMessageRow(
            ticket_id=ticket_id,
            sender=agent,
            message=message,
        )

        db.add(
            support_message
        )

        db.add(
            AuditRow(
                ticket_id=ticket_id,
                event_type="HUMAN_SUPPORT_MESSAGE",
                actor=agent,
                description=(
                    "Human support agent sent "
                    "a response to the customer."
                ),
                metadata_json={
                    "message": message,
                },
            )
        )

        db.commit()

        db.refresh(
            support_message
        )

        return {
            "id": support_message.id,
            "ticket_id": support_message.ticket_id,
            "sender": support_message.sender,
            "message": support_message.message,
            "created_at": support_message.created_at,
            "status": ticket.status,
        }


# ============================================================
# CLOSE TICKET
# ============================================================

@app.post("/tickets/{ticket_id}/close")
def close_ticket(ticket_id: str):

    with SessionLocal() as db:

        ticket = (
            db.query(TicketRow)
            .filter_by(
                ticket_id=ticket_id
            )
            .first()
        )

        if not ticket:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found",
            )

        if ticket.status == "DONE":

            return {
                "ticket_id": ticket_id,
                "status": "DONE",
                "message": "Ticket is already closed.",
            }

        ticket.status = "DONE"

        db.add(
            AuditRow(
                ticket_id=ticket_id,
                event_type="TICKET_CLOSED",
                actor="support_agent",
                description=(
                    "Ticket resolved and closed "
                    "by human support agent."
                ),
                metadata_json={},
            )
        )

        db.commit()

        return {
            "ticket_id": ticket_id,
            "status": "DONE",
            "message": "Ticket marked as done.",
        }


# ============================================================
# AI INVESTIGATION
# ============================================================

@app.post("/tickets/{ticket_id}/investigate")
def inv(
    ticket_id: str,
    body: dict,
):

    try:

        question = (
            body.get(
                "question",
                ""
            )
            .strip()
        )

        if not question:
            raise ValueError(
                "Question is required."
            )

        return investigate(
            ticket_id,
            question,
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "AI investigation failed: "
                f"{type(e).__name__}: {e}"
            ),
        )


# ============================================================
# HUMAN FEEDBACK
# ============================================================

@app.post("/tickets/{ticket_id}/feedback")
def feedback(
    ticket_id: str,
    body: FeedbackRequest,
):

    try:

        return submit_feedback(
            ticket_id=ticket_id,
            human_category=body.human_category,
            human_severity=body.human_severity.value,
            human_escalate=body.human_escalate,
            reason=body.reason,
            analyst=body.analyst,
        )

    except ValueError as e:

        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# ============================================================
# LEARNING STATS
# ============================================================

@app.get("/learning/stats")
def learning_stats():

    return get_learning_stats()


# ============================================================
# LEARNING RUN
# ============================================================

@app.post("/learning/run")
def learning_run():

    try:

        return run_learning_cycle()

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )