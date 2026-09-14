from app.models import Ticket, Analysis, Decision, Investigation
from app.rag import retrieve
from app.ollama_client import analyze_ticket, investigate_ticket
from app.db import SessionLocal, TicketRow, AnalysisRow, log_event
from app.learning import learning_context


def process_ticket(t):
    log_event(t.ticket_id, "TICKET_RECEIVED", "system", "Support ticket received.")
    kb = retrieve(t.subject + " " + t.message)
    text = "\n\n".join(f"[{x.title}]\n{x.content}" for x in kb)
    log_event(
        t.ticket_id,
        "KNOWLEDGE_BASE_SEARCH",
        "ai_agent",
        f"Retrieved {len(kb)} documents.",
        {"documents": [x.title for x in kb]},
    )

    learned = learning_context(t.subject + " " + t.message)
    log_event(
        t.ticket_id,
        "LEARNING_MEMORY_SEARCH",
        "learning_engine",
        "Retrieved validated human examples for this ticket.",
        {"available": "No validated human examples are available yet." not in learned},
    )

    a = Analysis.model_validate(analyze_ticket(t, text, learned))
    status = "ESCALATED" if a.escalate else ("REVIEW" if a.confidence < .75 else "AI_RESOLVED")
    with SessionLocal() as db:
        row = db.query(TicketRow).filter_by(ticket_id=t.ticket_id).first()
        if not row:
            row = TicketRow(ticket_id=t.ticket_id, customer_name=t.customer_name, subject=t.subject, message=t.message)
            db.add(row)
        row.category = a.category
        row.severity = a.severity.value
        row.confidence = a.confidence
        row.status = status
        row.team = a.assigned_team
        db.add(AnalysisRow(ticket_id=t.ticket_id, data=a.model_dump(mode="json")))
        db.commit()

    log_event(
        t.ticket_id,
        "AI_CLASSIFIED",
        "ai_agent",
        f"Classified as {a.category} with {a.confidence:.0%} confidence.",
        a.model_dump(mode="json"),
    )
    log_event(
        t.ticket_id,
        "ESCALATION_TRIGGERED" if a.escalate else ("RESOLUTION_ATTEMPTED" if status == "AI_RESOLVED" else "HUMAN_REVIEW_REQUIRED"),
        "ai_agent",
        a.escalation_reason if a.escalate else "AI decision recorded.",
        {"team": a.assigned_team},
    )
    return Decision(analysis=a, knowledge=kb)


def investigate(ticket_id, q):
    with SessionLocal() as db:
        t = db.query(TicketRow).filter_by(ticket_id=ticket_id).first()
        ar = db.query(AnalysisRow).filter_by(ticket_id=ticket_id).order_by(AnalysisRow.created_at.desc()).first()
    if not t or not ar:
        raise ValueError("Ticket has not been analyzed.")

    ticket = Ticket(ticket_id=t.ticket_id, customer_name=t.customer_name, subject=t.subject, message=t.message)
    kb = retrieve(t.subject + " " + t.message + " " + q)
    kb_text = "\n\n".join(x.content for x in kb)
    learned = learning_context(t.subject + " " + t.message + " " + q)
    res = Investigation.model_validate(investigate_ticket(ticket, ar.data, kb_text, q, learned))
    log_event(
        ticket_id,
        "AI_INVESTIGATION",
        "investigation_agent",
        f"Investigated: {q}",
        res.model_dump(mode="json"),
    )
    return res
