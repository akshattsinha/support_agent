import json
import httpx

from app.config import settings


SYSTEM = """
You are a conservative enterprise support triage agent.

Never claim privileged actions happened.

Never invent customer information,
transactions, refunds, account changes,
support policies, or system events.

Use supplied knowledge as the source of truth.

Escalate assessment, security, billing disputes,
policy decisions, high-impact cases, and uncertain
cases.
"""


# ============================================================
# GENERIC OLLAMA GENERATION
# ============================================================

def gen(prompt):

    payload = {
        "model":
            settings.ollama_model,

        "system":
            SYSTEM,

        "prompt":
            prompt,

        "stream":
            False,

        "think":
            False,

        "format":
            "json",

        "options": {
            "temperature": 0.1,
        },
    }

    with httpx.Client(
        timeout=180
    ) as client:

        response = client.post(
            (
                f"{settings.ollama_base_url.rstrip('/')}"
                "/api/generate"
            ),
            json=payload,
        )

        response.raise_for_status()

        data = response.json()

        raw = data.get(
            "response",
            "",
        )

        if not raw:

            raise RuntimeError(
                "Ollama returned an empty response."
            )

        try:

            return json.loads(
                raw
            )

        except json.JSONDecodeError as exc:

            raise RuntimeError(
                "Ollama returned invalid JSON: "
                f"{raw[:500]}"
            ) from exc


# ============================================================
# TICKET ANALYSIS
# ============================================================

def analyze_ticket(
    ticket,
    knowledge,
    learning="",
):

    return gen(
        f"""
Analyze this support ticket.

Ticket ID:
{ticket.ticket_id}

Subject:
{ticket.subject}

Message:
{ticket.message}

Knowledge Base:
{knowledge}

Validated human examples from previous
reviewed cases:
{learning}

Return exactly these fields as JSON:

category
severity
urgency
sentiment
customer_impact
ai_resolvable
escalate
assigned_team
confidence
escalation_reason
recommended_action

Rules:

- severity must be LOW, MEDIUM, HIGH, or CRITICAL.
- confidence must be between 0 and 1.
- Be conservative.
- Do not invent facts.
- Billing disputes should generally be escalated.
- Security concerns should generally be escalated.
- Assessment problems with possible impact on
  an active assessment should generally be escalated.
- If the knowledge base does not safely answer
  the customer's question, escalate.
- Only set ai_resolvable=true when the issue can
  be safely answered from the knowledge provided.
- Do not claim that any action has already happened.
"""
    )


# ============================================================
# AI INVESTIGATION
# ============================================================

def investigate_ticket(
    ticket,
    analysis,
    knowledge,
    question,
    learning="",
):

    result = gen(
        f"""
Investigate this support case.

Ticket:
{ticket.message}

Existing AI analysis:
{json.dumps(
    analysis,
    default=str,
)}

Knowledge Base:
{knowledge}

Validated human examples from previous
reviewed cases:
{learning}

Question:
{question}

Return exactly:

{{
  "findings": "string",
  "evidence": [
    "string",
    "string"
  ],
  "recommendation": "string",
  "confidence": 0.0
}}

IMPORTANT:

- evidence MUST be a JSON array of strings.
- Never return evidence as a single string.
- Do not invent logs, events, customer information,
  or facts.
- Only include evidence actually supported by
  the ticket, existing analysis, or knowledge base.
- Previous human examples are decision guidance
  only and are NOT evidence about this ticket.
- confidence must be between 0 and 1.
"""
    )

    evidence = result.get(
        "evidence",
        [],
    )

    if isinstance(
        evidence,
        str,
    ):

        evidence = [
            evidence
        ]

    elif evidence is None:

        evidence = []

    elif not isinstance(
        evidence,
        list,
    ):

        evidence = [
            str(evidence)
        ]

    result["evidence"] = [
        str(item)
        for item in evidence
    ]

    result["findings"] = str(
        result.get(
            "findings",
            "",
        )
    )

    result["recommendation"] = str(
        result.get(
            "recommendation",
            "",
        )
    )

    try:

        result["confidence"] = float(
            result.get(
                "confidence",
                0.0,
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        result["confidence"] = 0.0

    result["question"] = question

    return result


# Backwards-compatible alias
analyze_ticket = analyze_ticket