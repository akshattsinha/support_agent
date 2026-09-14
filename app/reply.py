import re
from pathlib import Path
from typing import List, Dict

from app.config import settings
from app.ollama_client import gen


# ============================================================
# KNOWLEDGE BASE TOPIC SIGNALS
# ============================================================

TOPIC_KEYWORDS = {
    "account_login.md": {
        "password",
        "login",
        "log",
        "logged",
        "signin",
        "sign",
        "account",
        "credentials",
        "forgot",
        "reset",
        "authentication",
        "access",
        "locked",
        "username",
        "email",
    },

    "billing.md": {
        "billing",
        "bill",
        "charge",
        "charged",
        "charging",
        "payment",
        "paid",
        "pay",
        "invoice",
        "refund",
        "subscription",
        "duplicate",
        "twice",
        "money",
        "credit",
        "debit",
        "price",
        "amount",
        "transaction",
        "fee",
    },

    "security.md": {
        "security",
        "hacked",
        "hack",
        "unauthorized",
        "unauthorised",
        "suspicious",
        "breach",
        "breached",
        "attacker",
        "attack",
        "stolen",
        "compromised",
        "intruder",
        "fraud",
        "phishing",
        "malicious",
        "unknown",
        "someone",
        "accessed",
        "access",
        "device",
        "session",
    },

    "assessment_issues.md": {
        "assessment",
        "test",
        "exam",
        "interview",
        "submission",
        "submitted",
        "submit",
        "browser",
        "crash",
        "crashed",
        "timeout",
        "timed",
        "question",
        "coding",
        "candidate",
        "proctor",
        "proctoring",
        "assessment",
    },
}


# ============================================================
# LOAD KNOWLEDGE BASE
# ============================================================

def load_knowledge_base() -> List[Dict[str, str]]:
    """
    Load all markdown knowledge-base documents.
    """

    kb_dir = Path(
        settings.knowledge_base_dir
    )

    if not kb_dir.exists():
        return []

    documents = []

    for path in sorted(
        kb_dir.glob("*.md")
    ):

        try:

            content = path.read_text(
                encoding="utf-8"
            ).strip()

        except Exception:

            continue

        if not content:
            continue

        documents.append(
            {
                "name": path.name,
                "content": content,
            }
        )

    return documents


# ============================================================
# TOKENIZATION
# ============================================================

def _tokens(text: str) -> set:
    """
    Convert text into normalized word tokens.
    """

    return set(
        re.findall(
            r"[a-zA-Z0-9]+",
            text.lower(),
        )
    )


# ============================================================
# QUERY NORMALIZATION
# ============================================================

def _normalize_query(text: str) -> set:
    """
    Add lightweight semantic aliases so common
    customer language maps to support terminology.
    """

    tokens = _tokens(text)

    aliases = {
        "charged": {
            "charge",
            "billing",
            "payment",
        },

        "charging": {
            "charge",
            "billing",
            "payment",
        },

        "paid": {
            "payment",
            "billing",
        },

        "twice": {
            "duplicate",
            "billing",
            "charge",
        },

        "hacked": {
            "security",
            "unauthorized",
        },

        "accessed": {
            "security",
            "unauthorized",
        },

        "attacked": {
            "security",
            "attack",
        },

        "stolen": {
            "security",
            "compromised",
        },

        "crashed": {
            "browser",
            "assessment",
        },

        "crash": {
            "browser",
            "assessment",
        },

        "forgot": {
            "password",
            "login",
        },

        "locked": {
            "account",
            "login",
        },

        "refund": {
            "billing",
            "payment",
        },

        "invoice": {
            "billing",
        },

        "subscription": {
            "billing",
        },
    }

    expanded = set(tokens)

    for token in tokens:

        expanded.update(
            aliases.get(
                token,
                set(),
            )
        )

    return expanded


# ============================================================
# DOCUMENT SCORING
# ============================================================

def _score_document(
    query_tokens: set,
    document: Dict[str, str],
) -> float:

    name = document["name"]

    content_tokens = _tokens(
        document["content"]
    )

    topic_tokens = TOPIC_KEYWORDS.get(
        name,
        set(),
    )

    score = 0.0

    # --------------------------------------------------------
    # Content overlap
    # --------------------------------------------------------

    content_matches = (
        query_tokens
        & content_tokens
    )

    score += (
        len(content_matches)
        * 1.0
    )

    # --------------------------------------------------------
    # Strong topic keyword overlap
    # --------------------------------------------------------

    topic_matches = (
        query_tokens
        & topic_tokens
    )

    score += (
        len(topic_matches)
        * 4.0
    )

    # --------------------------------------------------------
    # Exact filename/topic signals
    # --------------------------------------------------------

    filename = name.lower()

    for token in query_tokens:

        if (
            token in filename
        ):

            score += 3.0

    return score


# ============================================================
# RETRIEVE KNOWLEDGE
# ============================================================

def retrieve_reply_context(
    ticket_text: str,
    limit: int = 4,
) -> List[Dict[str, str]]:

    documents = load_knowledge_base()

    if not documents:

        return []

    query_tokens = _normalize_query(
        ticket_text
    )

    scored = []

    for document in documents:

        score = _score_document(
            query_tokens,
            document,
        )

        scored.append(
            (
                score,
                document,
            )
        )

    scored.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # Only return documents with meaningful relevance.
    # --------------------------------------------------------

    results = []

    for score, document in scored:

        if score <= 0:
            continue

        results.append(
            document
        )

        if len(results) >= limit:
            break

    return results


# ============================================================
# GROUNDED REPLY GENERATION
# ============================================================

def generate_grounded_reply(
    ticket,
    analysis: dict,
) -> dict:

    ticket_text = (
        f"Subject: {ticket.subject}\n"
        f"Message: {ticket.message}"
    )

    knowledge = retrieve_reply_context(
        ticket_text,
        limit=settings.top_k,
    )

    escalate = bool(
        analysis.get(
            "escalate",
            False,
        )
    )

    ai_resolvable = bool(
        analysis.get(
            "ai_resolvable",
            False,
        )
    )

    severity = str(
        analysis.get(
            "severity",
            "HIGH",
        )
    ).upper()

    try:

        confidence = float(
            analysis.get(
                "confidence",
                0.0,
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        confidence = 0.0

    sources = [
        document["name"]
        for document in knowledge
    ]

    # ========================================================
    # SAFETY GATES
    # ========================================================

    if escalate:

        return {
            "can_reply": False,
            "reply": "",
            "sources": sources,
            "reason": (
                "The ticket was classified "
                "for human escalation."
            ),
            "confidence": confidence,
        }

    if not ai_resolvable:

        return {
            "can_reply": False,
            "reply": "",
            "sources": sources,
            "reason": (
                "The ticket cannot be safely "
                "resolved automatically."
            ),
            "confidence": confidence,
        }

    if severity in {
        "HIGH",
        "CRITICAL",
    }:

        return {
            "can_reply": False,
            "reply": "",
            "sources": sources,
            "reason": (
                "High-impact tickets require "
                "human review."
            ),
            "confidence": confidence,
        }

    if confidence < 0.75:

        return {
            "can_reply": False,
            "reply": "",
            "sources": sources,
            "reason": (
                "AI confidence is below the "
                "automatic reply threshold."
            ),
            "confidence": confidence,
        }

    # ========================================================
    # KNOWLEDGE CONTEXT
    # ========================================================

    if not knowledge:

        return {
            "can_reply": False,
            "reply": "",
            "sources": [],
            "reason": (
                "No relevant knowledge-base "
                "article was found."
            ),
            "confidence": confidence,
        }

    knowledge_text = "\n\n".join(
        [
            (
                f"SOURCE: {document['name']}\n"
                f"{document['content']}"
            )
            for document in knowledge
        ]
    )

    # ========================================================
    # LLM RESPONSE
    # ========================================================

    result = gen(
        f"""
You are a customer-support response agent.

Write a concise and professional response
to the customer.

CUSTOMER TICKET

Ticket ID:
{ticket.ticket_id}

Subject:
{ticket.subject}

Message:
{ticket.message}

AI TRIAGE

Category:
{analysis.get("category", "Unknown")}

Severity:
{severity}

Confidence:
{confidence:.2f}

RELEVANT SUPPORT KNOWLEDGE

{knowledge_text}

STRICT RULES

1. Answer ONLY using information supported
   by the supplied support knowledge.

2. Never invent policies, refunds, timelines,
   account actions, technical facts, or
   customer information.

3. Never claim that an action has been completed
   unless the supplied information explicitly
   proves it.

4. Never expose internal AI reasoning.

5. Do not mention the knowledge base.

6. If the information is insufficient to answer
   safely, return can_reply=false.

7. Keep the customer response concise.

Return exactly:

{{
    "can_reply": true,
    "reply": "customer-facing response",
    "reason": "short reason",
    "confidence": 0.0
}}
"""
    )

    can_reply = bool(
        result.get(
            "can_reply",
            False,
        )
    )

    reply = str(
        result.get(
            "reply",
            "",
        )
    ).strip()

    reason = str(
        result.get(
            "reason",
            "",
        )
    ).strip()

    try:

        reply_confidence = float(
            result.get(
                "confidence",
                confidence,
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        reply_confidence = confidence

    reply_confidence = max(
        0.0,
        min(
            1.0,
            reply_confidence,
        ),
    )

    if not can_reply or not reply:

        return {
            "can_reply": False,
            "reply": "",
            "sources": sources,
            "reason": (
                reason
                or
                "The AI could not safely "
                "generate a response."
            ),
            "confidence":
                reply_confidence,
        }

    return {
        "can_reply": True,
        "reply": reply,
        "sources": sources,
        "reason": reason,
        "confidence":
            reply_confidence,
    }