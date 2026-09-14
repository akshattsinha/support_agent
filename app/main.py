from fastapi import FastAPI, HTTPException
from app.models import Ticket, FeedbackRequest
from app.agent import process_ticket, investigate
from app.db import SessionLocal, TicketRow, AnalysisRow, AuditRow
from app.learning import submit_feedback, get_learning_stats, run_learning_cycle

app = FastAPI(title="AI Support Sentinel", version="2.1")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/tickets/process")
def process(t: Ticket):
    try:
        return process_ticket(t)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/tickets")
def tickets():
    with SessionLocal() as db:
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
            for r in db.query(TicketRow).order_by(TicketRow.created_at.desc()).all()
        ]


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    with SessionLocal() as db:
        t = db.query(TicketRow).filter_by(ticket_id=ticket_id).first()
        a = db.query(AnalysisRow).filter_by(ticket_id=ticket_id).order_by(AnalysisRow.created_at.desc()).first()
        es = db.query(AuditRow).filter_by(ticket_id=ticket_id).order_by(AuditRow.timestamp.asc()).all()
        if not t:
            raise HTTPException(404, "Ticket not found")
        return {
            "ticket": {c: getattr(t, c) for c in ["ticket_id", "customer_name", "subject", "message", "category", "severity", "confidence", "status", "team", "created_at"]},
            "analysis": a.data if a else None,
            "audit": [
                {"event_type": e.event_type, "actor": e.actor, "description": e.description, "metadata": e.metadata_json, "timestamp": e.timestamp}
                for e in es
            ],
        }


@app.post("/tickets/{ticket_id}/investigate")
def inv(ticket_id: str, body: dict):
    try:
        question = body.get("question", "").strip()
        if not question:
            raise ValueError("Question is required.")
        return investigate(ticket_id, question)
    except Exception as e:
        raise HTTPException(500, f"AI investigation failed: {type(e).__name__}: {e}")


@app.post("/tickets/{ticket_id}/feedback")
def feedback(ticket_id: str, body: FeedbackRequest):
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
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/learning/stats")
def learning_stats():
    return get_learning_stats()


@app.post("/learning/run")
def learning_run():
    try:
        return run_learning_cycle()
    except Exception as e:
        raise HTTPException(500, str(e))
