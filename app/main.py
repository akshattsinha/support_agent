from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

from app.models import Ticket, FeedbackRequest
from app.agent import process_ticket, investigate
from app.reply import generate_grounded_reply

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
    version="3.0",
)


# ============================================================
# REQUEST MODELS
# ============================================================

class SupportMessageRequest(BaseModel):
    message: str
    agent: str = "support_agent"


class BatchTicketRequest(BaseModel):
    tickets: List[Ticket]


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "AI Support Sentinel",
    }


# ============================================================
# PROCESS ONE TICKET
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
# PROCESS TICKET BATCH
# ============================================================

@app.post("/tickets/process-batch")
def process_batch(body: BatchTicketRequest):

    if not body.tickets:

        raise HTTPException(
            status_code=400,
            detail="At least one ticket is required.",
        )

    results = []

    for ticket in body.tickets:

        try:

            result = process_ticket(ticket)

            results.append(
                {
                    "ticket_id": ticket.ticket_id,
                    "success": True,
                    "result": result,
                }
            )

        except Exception as e:

            results.append(
                {
                    "ticket_id": ticket.ticket_id,
                    "success": False,
                    "error": str(e),
                }
            )

    successful = sum(
        1
        for item in results
        if item["success"]
    )

    failed = len(results) - successful

    return {
        "total": len(results),
        "successful": successful,
        "failed": failed,
        "results": results,
    }


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
# IMPORTANT:
# THIS MUST COME BEFORE /tickets/{ticket_id}
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
                TicketRow.created_at.asc()
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
# TICKET DETAIL
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
                c: getattr(
                    ticket,
                    c,
                )
                for c in [
                    "ticket_id",
                    "customer_name",
                    "subject",
                    "message",
                    "category",
                    "severity",
                    "confidence",
                    "status",
                    "team",
                    "created_at",
                ]
            },
            "analysis": (
                analysis.data
                if analysis
                else None
            ),
            "audit": [
                {
                    "event_type":
                        event.event_type,

                    "actor":
                        event.actor,

                    "description":
                        event.description,

                    "metadata":
                        event.metadata_json,

                    "timestamp":
                        event.timestamp,
                }
                for event in events
            ],
        }


# ============================================================
# GENERATE GROUNDED AI REPLY
# ============================================================

@app.post("/tickets/{ticket_id}/reply")
def generate_reply(ticket_id: str):

    try:

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

            analysis_row = (
                db.query(AnalysisRow)
                .filter_by(
                    ticket_id=ticket_id
                )
                .order_by(
                    AnalysisRow.created_at.desc()
                )
                .first()
            )

            if not analysis_row:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "This ticket has not been "
                        "analyzed yet. Process the "
                        "ticket first."
                    ),
                )

            analysis = dict(
                analysis_row.data
            )

            # ------------------------------------------------
            # DO NOT AUTO-REPLY TO ESCALATED CASES
            # ------------------------------------------------

            if (
                ticket.status
                in [
                    "ESCALATED",
                    "HUMAN_ACTIVE",
                    "DONE",
                ]
            ):

                return {
                    "can_reply": False,
                    "reply": "",
                    "sources": [],
                    "reason": (
                        "This ticket is currently "
                        "handled through the human "
                        "support workflow."
                    ),
                    "confidence": float(
                        analysis.get(
                            "confidence",
                            0.0,
                        )
                    ),
                }

            result = generate_grounded_reply(
                ticket,
                analysis,
            )

            # ------------------------------------------------
            # STORE REPLY IN ANALYSIS
            # ------------------------------------------------

            if result["can_reply"]:

                updated_analysis = dict(
                    analysis
                )

                updated_analysis[
                    "generated_reply"
                ] = result["reply"]

                updated_analysis[
                    "reply_sources"
                ] = result["sources"]

                updated_analysis[
                    "reply_confidence"
                ] = result["confidence"]

                updated_analysis[
                    "reply_status"
                ] = "GENERATED"

                analysis_row.data = (
                    updated_analysis
                )

                db.commit()

                # --------------------------------------------
                # AUDIT
                # --------------------------------------------

                db.add(
                    AuditRow(
                        ticket_id=ticket_id,
                        event_type="AI_REPLY_GENERATED",
                        actor="ai",
                        description=(
                            "Generated a grounded "
                            "customer response using "
                            "retrieved knowledge."
                        ),
                        metadata_json={
                            "sources":
                                result["sources"],

                            "confidence":
                                result[
                                    "confidence"
                                ],
                        },
                    )
                )

                db.commit()

            return result

    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "AI reply generation failed: "
                f"{type(e).__name__}: {e}"
            ),
        )


# ============================================================
# INVESTIGATION
# ============================================================

@app.post("/tickets/{ticket_id}/investigate")
def inv(
    ticket_id: str,
    body: dict,
):

    try:

        question = (
            body
            .get(
                "question",
                "",
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
            human_category=
                body.human_category,

            human_severity=
                body.human_severity.value,

            human_escalate=
                body.human_escalate,

            reason=
                body.reason,

            analyst=
                body.analyst,
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
# SUPPORT CHAT
# ============================================================

@app.get(
    "/tickets/{ticket_id}/messages"
)
def get_messages(ticket_id: str):

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

        stored_messages = (
            db.query(
                SupportMessageRow
            )
            .filter_by(
                ticket_id=ticket_id
            )
            .order_by(
                SupportMessageRow.created_at.asc()
            )
            .all()
        )

        # ----------------------------------------------------
        # ALWAYS PRESERVE ORIGINAL CUSTOMER MESSAGE
        # ----------------------------------------------------

        messages = [
            {
                "id": 0,
                "sender": "customer",
                "message": ticket.message,
                "created_at": ticket.created_at,
            }
        ]

        messages.extend(
            [
                {
                    "id": message.id,
                    "sender": message.sender,
                    "message": message.message,
                    "created_at":
                        message.created_at,
                }
                for message
                in stored_messages
            ]
        )

        return messages


# ============================================================
# SEND SUPPORT MESSAGE
# ============================================================

@app.post(
    "/tickets/{ticket_id}/messages"
)
def send_message(
    ticket_id: str,
    body: SupportMessageRequest,
):

    message = body.message.strip()

    if not message:

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
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
                detail=(
                    "This ticket is already closed."
                ),
            )

        if ticket.status == "ESCALATED":

            ticket.status = "HUMAN_ACTIVE"

        support_message = (
            SupportMessageRow(
                ticket_id=ticket_id,
                sender=(
                    body.agent.strip()
                    or "support_agent"
                ),
                message=message,
            )
        )

        db.add(
            support_message
        )

        db.flush()

        db.add(
            AuditRow(
                ticket_id=ticket_id,
                event_type="HUMAN_SUPPORT_MESSAGE",
                actor=(
                    body.agent.strip()
                    or "support_agent"
                ),
                description=(
                    "Support agent sent a "
                    "message to the customer."
                ),
                metadata_json={
                    "message_id":
                        support_message.id,
                },
            )
        )

        db.commit()

        return {
            "success": True,
            "message_id":
                support_message.id,
            "status":
                ticket.status,
        }


# ============================================================
# CLOSE TICKET
# ============================================================

@app.post(
    "/tickets/{ticket_id}/close"
)
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
                "success": True,
                "status": "DONE",
                "message": (
                    "Ticket was already closed."
                ),
            }

        ticket.status = "DONE"

        db.add(
            AuditRow(
                ticket_id=ticket_id,
                event_type="TICKET_CLOSED",
                actor="support_agent",
                description=(
                    "Support agent marked the "
                    "ticket as resolved."
                ),
                metadata_json={
                    "final_status": "DONE",
                },
            )
        )

        db.commit()

        return {
            "success": True,
            "status": "DONE",
        }


# ============================================================
# CONTINUAL LEARNING
# ============================================================

@app.get("/learning/stats")
def learning_stats():

    return get_learning_stats()


@app.post("/learning/run")
def learning_run():

    try:

        return run_learning_cycle()

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )