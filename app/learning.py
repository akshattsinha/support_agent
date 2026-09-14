"""Human-in-the-loop continual learning for AI Support Sentinel.

This module intentionally does not fine-tune the LLM after every ticket. It
captures validated analyst corrections, retrieves similar corrected cases for
future prompts, and evaluates accumulated feedback in periodic learning runs.
"""
from collections import Counter
from datetime import datetime, timedelta
import re

from app.db import (
    SessionLocal,
    TicketRow,
    AnalysisRow,
    FeedbackRow,
    LearningExampleRow,
    LearningRunRow,
    log_event,
)

STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "for", "in", "on", "is",
    "it", "this", "that", "with", "my", "i", "we", "you", "are", "was",
    "be", "from", "at", "as", "have", "has", "had", "but", "not", "can",
    "please", "why", "what", "how", "should", "could", "would",
}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}


def _similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(1, len(ta | tb))


def submit_feedback(
    ticket_id: str,
    human_category: str,
    human_severity: str,
    human_escalate: bool,
    reason: str = "",
    analyst: str = "analyst",
):
    with SessionLocal() as db:
        ticket = db.query(TicketRow).filter_by(ticket_id=ticket_id).first()
        analysis = (
            db.query(AnalysisRow)
            .filter_by(ticket_id=ticket_id)
            .order_by(AnalysisRow.created_at.desc())
            .first()
        )

        if not ticket or not analysis:
            raise ValueError("Ticket has not been analyzed.")

        # Copy all values we need while the SQLAlchemy session is active.
        ticket_subject = ticket.subject
        ticket_message = ticket.message
        ticket_category = ticket.category
        ticket_severity = ticket.severity

        ai = dict(analysis.data or {})

        ai_category = str(ai.get("category", ticket_category))
        ai_severity = str(ai.get("severity", ticket_severity))
        ai_escalate = bool(ai.get("escalate", False))

        changed = {
            "category": ai_category != human_category,
            "severity": ai_severity != human_severity,
            "escalate": ai_escalate != bool(human_escalate),
        }

        corrections = sum(changed.values())

        feedback = FeedbackRow(
            ticket_id=ticket_id,
            analyst=analyst or "analyst",
            ai_category=ai_category,
            human_category=human_category,
            ai_severity=ai_severity,
            human_severity=human_severity,
            ai_escalate=ai_escalate,
            human_escalate=bool(human_escalate),
            reason=reason or "",
        )

        db.add(feedback)
        db.flush()

        # Store the validated human correction as a reusable learning example.
        example = LearningExampleRow(
            ticket_id=ticket_id,
            input_text=f"Subject: {ticket_subject}\nMessage: {ticket_message}",
            corrected_output={
                "category": human_category,
                "severity": human_severity,
                "escalate": bool(human_escalate),
            },
            reason=reason or "",
            source_feedback_id=feedback.id,
        )

        db.add(example)
        db.commit()

        feedback_id = feedback.id

    log_event(
        ticket_id,
        "HUMAN_FEEDBACK",
        analyst or "analyst",
        "Human feedback captured for continual learning.",
        {
            "feedback_id": feedback_id,
            "changed_fields": [
                k for k, v in changed.items() if v
            ],
        },
    )

    return {
        "feedback_id": feedback_id,
        "ticket_id": ticket_id,
        "corrections": corrections,
        "changed_fields": [
            k for k, v in changed.items() if v
        ],
    }


def retrieve_learning_examples(text: str, limit: int = 3) -> list[dict]:
    """Return the most similar validated human corrections."""
    with SessionLocal() as db:
        examples = db.query(LearningExampleRow).order_by(LearningExampleRow.created_at.desc()).limit(500).all()
        scored = [
            (_similarity(text, ex.input_text), ex)
            for ex in examples
        ]
    scored.sort(key=lambda x: (x[0], x[1].created_at), reverse=True)
    return [
        {
            "similarity": round(score, 3),
            "ticket_id": ex.ticket_id,
            "input_text": ex.input_text,
            "corrected_output": ex.corrected_output,
            "reason": ex.reason,
        }
        for score, ex in scored[:limit]
        if score > 0
    ]


def learning_context(text: str, limit: int = 3) -> str:
    examples = retrieve_learning_examples(text, limit=limit)
    if not examples:
        return "No validated human examples are available yet."

    blocks = []
    for i, ex in enumerate(examples, 1):
        blocks.append(
            f"[Validated Example {i} | similarity={ex['similarity']}]\n"
            f"{ex['input_text']}\n"
            f"Human-corrected decision: {ex['corrected_output']}\n"
            f"Reason: {ex['reason'] or 'Not provided'}"
        )
    return "\n\n".join(blocks)


def run_learning_cycle() -> dict:
    """Evaluate accumulated feedback and persist a learning-run snapshot."""
    with SessionLocal() as db:
        feedback = db.query(FeedbackRow).order_by(FeedbackRow.created_at.asc()).all()

        total = len(feedback)
        corrections = 0
        category_changes = Counter()
        severity_changes = Counter()
        escalation_changes = 0
        for f in feedback:
            if f.ai_category != f.human_category:
                corrections += 1
                category_changes[f"{f.ai_category} → {f.human_category}"] += 1
            if f.ai_severity != f.human_severity:
                corrections += 1
                severity_changes[f"{f.ai_severity} → {f.human_severity}"] += 1
            if f.ai_escalate != f.human_escalate:
                corrections += 1
                escalation_changes += 1

        # Agreement is measured across the three supervised decisions.
        opportunities = total * 3
        agreement_rate = 1.0 if opportunities == 0 else max(0.0, 1 - corrections / opportunities)
        summary = {
            "feedback_count": total,
            "field_corrections": corrections,
            "agreement_rate": round(agreement_rate, 4),
            "top_category_corrections": category_changes.most_common(5),
            "top_severity_corrections": severity_changes.most_common(5),
            "escalation_corrections": escalation_changes,
            "learning_examples": db.query(LearningExampleRow).count(),
        }
        run = LearningRunRow(
            feedback_count=total,
            corrections=corrections,
            agreement_rate=agreement_rate,
            status="COMPLETED",
            summary=summary,
        )
        db.add(run)
        db.commit()
        run_id = run.id

    log_event(
        "SYSTEM",
        "CONTINUAL_LEARNING_RUN",
        "learning_engine",
        f"Completed learning cycle #{run_id} using {total} validated feedback records.",
        summary,
    )
    return {"run_id": run_id, **summary}


def get_learning_stats() -> dict:
    with SessionLocal() as db:
        feedback = db.query(FeedbackRow).all()
        examples = db.query(LearningExampleRow).count()
        runs = db.query(LearningRunRow).order_by(LearningRunRow.created_at.desc()).limit(10).all()

        total = len(feedback)
        category_errors = sum(f.ai_category != f.human_category for f in feedback)
        severity_errors = sum(f.ai_severity != f.human_severity for f in feedback)
        escalation_errors = sum(f.ai_escalate != f.human_escalate for f in feedback)
        corrected = category_errors + severity_errors + escalation_errors
        agreement = 1.0 if total == 0 else max(0.0, 1 - corrected / (total * 3))

        recent_cutoff = datetime.utcnow() - timedelta(days=7)
        recent = [f for f in feedback if f.created_at and f.created_at >= recent_cutoff]

        return {
            "feedback_count": total,
            "learning_examples": examples,
            "field_corrections": corrected,
            "agreement_rate": round(agreement, 4),
            "category_corrections": category_errors,
            "severity_corrections": severity_errors,
            "escalation_corrections": escalation_errors,
            "feedback_last_7_days": len(recent),
            "recent_runs": [
                {
                    "id": r.id,
                    "created_at": r.created_at,
                    "feedback_count": r.feedback_count,
                    "corrections": r.corrections,
                    "agreement_rate": r.agreement_rate,
                }
                for r in runs
            ],
        }
