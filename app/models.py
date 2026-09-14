from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Ticket(BaseModel):
    ticket_id: str
    customer_name: str
    subject: str
    message: str
    category: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Analysis(BaseModel):
    category: str
    severity: Severity
    urgency: str
    sentiment: str
    customer_impact: str
    ai_resolvable: bool
    escalate: bool
    assigned_team: str
    confidence: float = Field(ge=0, le=1)
    escalation_reason: str
    recommended_action: str


class RAGResult(BaseModel):
    title: str
    content: str
    score: float


class Decision(BaseModel):
    analysis: Analysis
    knowledge: list[RAGResult] = []


class Investigation(BaseModel):
    question: str
    findings: str
    evidence: list[str]
    recommendation: str
    confidence: float = Field(ge=0, le=1)


class FeedbackRequest(BaseModel):
    human_category: str
    human_severity: Severity
    human_escalate: bool
    reason: str = ""
    analyst: str = "analyst"
