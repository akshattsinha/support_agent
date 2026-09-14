import json
from pathlib import Path

from app.db import SessionLocal, TicketRow, AnalysisRow


DATA_FILE = Path("data/tickets.json")


def make_analysis(t):
    severity = t["severity"]

    if severity == "CRITICAL":
        confidence = 0.89
        escalate = True
        ai_resolvable = False
        urgency = "IMMEDIATE"
        impact = "HIGH"

    elif severity == "HIGH":
        confidence = 0.91
        escalate = True
        ai_resolvable = False
        urgency = "HIGH"
        impact = "HIGH"

    elif severity == "MEDIUM":
        confidence = 0.86
        escalate = False
        ai_resolvable = False
        urgency = "NORMAL"
        impact = "MEDIUM"

    else:
        confidence = 0.97
        escalate = False
        ai_resolvable = True
        urgency = "LOW"
        impact = "LOW"

    return {
        "category": t["category"],
        "severity": severity,
        "urgency": urgency,
        "sentiment": "NEUTRAL",
        "customer_impact": impact,
        "ai_resolvable": ai_resolvable,
        "escalate": escalate,
        "assigned_team": t["team"],
        "confidence": confidence,
        "escalation_reason": (
            f"{severity} severity requires human review."
            if escalate
            else ""
        ),
        "recommended_action": (
            "Escalate to the assigned support team for human investigation."
            if escalate
            else "Provide the standard support resolution and monitor if needed."
        ),
    }


data = json.loads(DATA_FILE.read_text())

tickets_added = 0
analyses_added = 0

with SessionLocal() as db:

    # ---------------------------------------------------------
    # 1. Ensure all tickets exist
    # ---------------------------------------------------------
    for t in data:

        ticket = (
            db.query(TicketRow)
            .filter_by(ticket_id=t["ticket_id"])
            .first()
        )

        if ticket:
            continue

        severity = t["severity"]

        status = (
            "ESCALATED"
            if severity in ["HIGH", "CRITICAL"]
            else "REVIEW"
            if severity == "MEDIUM"
            else "AI_RESOLVED"
        )

        confidence = {
            "CRITICAL": 0.89,
            "HIGH": 0.91,
            "MEDIUM": 0.86,
            "LOW": 0.97,
        }[severity]

        db.add(
            TicketRow(
                ticket_id=t["ticket_id"],
                customer_name=t["customer_name"],
                subject=t["subject"],
                message=t["message"],
                category=t["category"],
                severity=severity,
                confidence=confidence,
                status=status,
                team=t["team"],
            )
        )

        tickets_added += 1

    db.commit()

    # ---------------------------------------------------------
    # 2. Create missing AI analyses
    # ---------------------------------------------------------
    for t in data:

        existing = (
            db.query(AnalysisRow)
            .filter_by(ticket_id=t["ticket_id"])
            .first()
        )

        if existing:
            continue

        analysis = make_analysis(t)

        db.add(
            AnalysisRow(
                ticket_id=t["ticket_id"],
                data=analysis,
            )
        )

        analyses_added += 1

    db.commit()


print(f"Tickets added: {tickets_added}")
print(f"AI analyses added: {analyses_added}")
print("Database seeding complete.")
