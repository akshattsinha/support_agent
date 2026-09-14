import sys
from pathlib import Path


# =============================================================================
# ADD PROJECT ROOT TO PYTHON PATH
# =============================================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

sys.path.insert(
    0,
    str(PROJECT_ROOT)
)


# =============================================================================
# IMPORT DATABASE
# =============================================================================

from app.db import (
    SessionLocal,
    TicketRow,
    AnalysisRow,
    AuditRow,
    FeedbackRow,
)


# =============================================================================
# CHECK EXISTING EVENT
# =============================================================================

def has_event(
    db,
    ticket_id,
    event_type,
):

    return (
        db.query(AuditRow)
        .filter_by(
            ticket_id=ticket_id,
            event_type=event_type,
        )
        .first()
        is not None
    )


# =============================================================================
# ADD EVENT
# =============================================================================

def add_event(
    db,
    ticket_id,
    event_type,
    actor,
    description,
    metadata,
    timestamp,
):

    # Prevent duplicates if the script is
    # executed more than once.

    if has_event(
        db,
        ticket_id,
        event_type,
    ):

        return False


    db.add(

        AuditRow(

            ticket_id=
                ticket_id,

            event_type=
                event_type,

            actor=
                actor,

            description=
                description,

            metadata_json=
                metadata or {},

            timestamp=
                timestamp,
        )
    )


    return True


# =============================================================================
# BACKFILL DATABASE
# =============================================================================

with SessionLocal() as db:

    tickets = (
        db.query(
            TicketRow
        ).all()
    )

    created = 0


    for ticket in tickets:

        # =====================================================================
        # GET ANALYSIS
        # =====================================================================

        analysis = (
            db.query(
                AnalysisRow
            )
            .filter_by(
                ticket_id=
                    ticket.ticket_id
            )
            .order_by(
                AnalysisRow.created_at.desc()
            )
            .first()
        )


        # =====================================================================
        # TICKET RECEIVED
        # =====================================================================

        if add_event(

            db,

            ticket.ticket_id,

            "TICKET_RECEIVED",

            "system",

            "Ticket was received and entered the AI Support Sentinel workflow.",

            {
                "subject":
                    ticket.subject,

                "customer_name":
                    ticket.customer_name,
            },

            ticket.created_at,

        ):

            created += 1


        # =====================================================================
        # AI ANALYSIS
        # =====================================================================

        if analysis:

            data = (
                analysis.data
                or {}
            )


            if add_event(

                db,

                ticket.ticket_id,

                "AI_ANALYSIS",

                "ai",

                "AI triage analysis was completed.",

                {

                    "category":
                        data.get(
                            "category"
                        ),

                    "severity":
                        data.get(
                            "severity"
                        ),

                    "confidence":
                        data.get(
                            "confidence"
                        ),

                    "ai_resolvable":
                        data.get(
                            "ai_resolvable"
                        ),
                },

                analysis.created_at,

            ):

                created += 1


            # =================================================================
            # KNOWLEDGE RETRIEVED
            # =================================================================

            if add_event(

                db,

                ticket.ticket_id,

                "KNOWLEDGE_RETRIEVED",

                "ai",

                "Knowledge-base context was used by the AI triage workflow.",

                {},

                analysis.created_at,

            ):

                created += 1


            # =================================================================
            # DECISION
            # =================================================================

            if data.get(
                "escalate"
            ):

                decision_type = (
                    "ESCALATION_DECISION"
                )

                description = (
                    "AI recommended escalation "
                    "for human handling."
                )

            else:

                decision_type = (
                    "RESOLUTION_DECISION"
                )

                description = (
                    "AI determined that escalation "
                    "was not required."
                )


            if add_event(

                db,

                ticket.ticket_id,

                decision_type,

                "ai",

                description,

                {

                    "escalate":
                        bool(
                            data.get(
                                "escalate"
                            )
                        ),

                    "assigned_team":
                        data.get(
                            "assigned_team"
                        ),

                    "reason":
                        data.get(
                            "escalation_reason",
                            "",
                        ),
                },

                analysis.created_at,

            ):

                created += 1


        # =====================================================================
        # EXISTING HUMAN FEEDBACK
        # =====================================================================

        feedback_rows = (

            db.query(
                FeedbackRow
            )

            .filter_by(
                ticket_id=
                    ticket.ticket_id
            )

            .order_by(
                FeedbackRow.created_at.asc(),
                FeedbackRow.id.asc(),
            )

            .all()
        )


        for feedback in feedback_rows:

            # =================================================================
            # HUMAN FEEDBACK EVENT
            # =================================================================

            if add_event(

                db,

                ticket.ticket_id,

                "HUMAN_FEEDBACK",

                feedback.analyst,

                "An analyst reviewed and corrected the AI assessment.",

                {

                    "feedback_id":
                        feedback.id,

                    "ai_category":
                        feedback.ai_category,

                    "human_category":
                        feedback.human_category,

                    "ai_severity":
                        feedback.ai_severity,

                    "human_severity":
                        feedback.human_severity,

                    "ai_escalate":
                        feedback.ai_escalate,

                    "human_escalate":
                        feedback.human_escalate,

                    "reason":
                        feedback.reason,
                },

                feedback.created_at,

            ):

                created += 1


            # =================================================================
            # LEARNING EXAMPLE
            # =================================================================

            changed_fields = []


            if (
                feedback.ai_category
                != feedback.human_category
            ):

                changed_fields.append(
                    "category"
                )


            if (
                feedback.ai_severity
                != feedback.human_severity
            ):

                changed_fields.append(
                    "severity"
                )


            if (
                feedback.ai_escalate
                != feedback.human_escalate
            ):

                changed_fields.append(
                    "escalate"
                )


            if add_event(

                db,

                ticket.ticket_id,

                "LEARNING_EXAMPLE_CREATED",

                "system",

                "Human feedback was stored as a validated learning example.",

                {

                    "feedback_id":
                        feedback.id,

                    "changed_fields":
                        changed_fields,
                },

                feedback.created_at,

            ):

                created += 1


    # ========================================================================
    # COMMIT
    # ========================================================================

    db.commit()


print(
    "Audit backfill complete. "
    f"Created {created} missing audit event(s)."
)