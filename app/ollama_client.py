import json
import httpx

from app.config import settings


SYSTEM = """You are a conservative enterprise support triage agent.
Never claim privileged actions happened.
Escalate assessment, security, billing disputes, policy decisions,
and uncertain cases.
"""


def gen(prompt):
    payload = {
        "model": settings.ollama_model,
        "system": SYSTEM,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "format": "json",
        "options": {
            "temperature": 0.1
        },
    }

    with httpx.Client(timeout=180) as client:
        response = client.post(
            f"{settings.ollama_base_url.rstrip('/')}/api/generate",
            json=payload,
        )

        response.raise_for_status()

        data = response.json()
        raw = data.get("response", "")

        if not raw:
            raise RuntimeError("Ollama returned an empty response.")

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Ollama returned invalid JSON: {raw[:500]}"
            ) from exc


def analyze_ticket(ticket, knowledge, learning=""):
    return gen(
        f"""Analyze this support ticket.

Ticket ID: {ticket.ticket_id}
Subject: {ticket.subject}
Message: {ticket.message}

Knowledge Base:
{knowledge}

Validated human examples from previous reviewed cases:
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
- Use validated human examples as decision guidance.
"""
    )


def investigate_ticket(ticket, analysis, knowledge, question, learning=""):
    result = gen(
        f"""Investigate this support case.

Ticket:
{ticket.message}

Existing AI analysis:
{json.dumps(analysis)}

Knowledge Base:
{knowledge}

Validated human examples from previous reviewed cases:
{learning}

Question:
{question}

Return exactly these fields as JSON:

{{
  "findings": "string",
  "evidence": ["string", "string"],
  "recommendation": "string",
  "confidence": 0.0
}}

IMPORTANT:
- evidence MUST be a JSON array of strings.
- Never return evidence as a single string.
- Do not invent logs, events, customer information, or facts.
- Only include evidence that is actually supported by the ticket, existing analysis, or knowledge base.
- Previous human examples are decision guidance only and are NOT evidence about this ticket.
- confidence must be a number between 0 and 1.
"""
    )

    # ---------------------------------------------------------
    # Normalize Ollama output before Pydantic validation.
    # ---------------------------------------------------------
    evidence = result.get("evidence", [])

    if isinstance(evidence, str):
        evidence = [evidence]
    elif evidence is None:
        evidence = []
    elif not isinstance(evidence, list):
        evidence = [str(evidence)]

    result["evidence"] = [str(item) for item in evidence]

    result["findings"] = str(
        result.get("findings", "")
    )

    result["recommendation"] = str(
        result.get("recommendation", "")
    )

    try:
        result["confidence"] = float(
            result.get("confidence", 0.0)
        )
    except (TypeError, ValueError):
        result["confidence"] = 0.0

    result["question"] = question

    return result
