# 🛡️ AI Support Sentinel

### AI-powered support triage, resolution, escalation, investigation, and continual learning

> **The goal is not to automate every support ticket. The goal is to
> make the right decision for every ticket.**

AI Support Sentinel is a support-operations prototype built for the
**support-ticket workflow**.

I approached the challenge as more than a classification problem. In a
real support environment, knowing what a ticket is about is only the
first step. The system also needs to decide whether an issue is safe to
resolve automatically, whether it needs a human, what information the
human needs, and how human corrections can improve future decisions.

That is the problem this project is designed around.

------------------------------------------------------------------------

## 🎯 The Problem

A support team may receive thousands of tickets covering everything from
simple password resets to billing disputes and security-sensitive
issues.

A useful AI support system therefore needs to answer several questions:

1.  **What is the customer asking about?**
2.  **How serious and urgent is it?**
3.  **Can the issue be safely resolved using known support knowledge?**
4.  **Should the AI respond, or should a human take over?**
5.  **If a human takes over, what evidence and context do they need?**
6.  **Can the system learn from the decisions humans make?**

AI Support Sentinel connects these steps into one workflow.

``` text
                 SUPPORT TICKET
                       │
                       ▼
                 ┌───────────┐
                 │ AI TRIAGE │
                 └─────┬─────┘
                       │
                       ▼
                ┌─────────────┐
                │ RAG / KB    │
                │ RETRIEVAL   │
                └──────┬──────┘
                       │
                       ▼
              ┌─────────────────┐
              │ RESOLUTION      │
              │ DECISION        │
              └───────┬─────────┘
                      │
             ┌────────┴────────┐
             ▼                 ▼
       SAFE TO RESOLVE     ESCALATE
             │                 │
             ▼                 ▼
      GROUNDED REPLY     HUMAN SUPPORT
                               │
                               ▼
                         INVESTIGATION
                               │
                               ▼
                          AUDIT TRAIL
                               │
                               ▼
                       HUMAN FEEDBACK
                               │
                               ▼
                      CONTINUAL LEARNING
```

------------------------------------------------------------------------

# 🧠 Core Design Principle

The central design decision is to **separate understanding from
action**.

A naive support chatbot looks like:

``` text
Ticket → LLM → Answer
```

AI Support Sentinel instead uses:

``` text
Ticket
  ↓
Understand
  ↓
Retrieve evidence
  ↓
Assess risk
  ↓
Decide
  ↓
Act
```

That distinction matters because an AI model can understand a ticket
correctly and still be the wrong system to handle it automatically.

For example:

``` text
HIGH severity
     ↓
Do not auto-resolve
     ↓
Escalate to human
```

or:

``` text
Low confidence
     ↓
Do not auto-reply
     ↓
Human review
```

This makes automation **risk-aware rather than answer-driven**.

------------------------------------------------------------------------

# 🚦 1. AI Triage

Each incoming ticket is analyzed for operational signals including:

-   Category
-   Severity
-   Sentiment
-   Urgency
-   Customer impact
-   Confidence
-   AI resolvability
-   Escalation decision
-   Assigned support team

The output is not simply a label.

The system uses the analysis to make a downstream **resolution
decision**.

### Example

A straightforward password-reset issue might be classified as:

``` text
Category: Password
Severity: LOW
Confidence: 97%
AI Resolvable: Yes
Escalate: No
```

A security-sensitive ticket can instead be routed toward human review.

This separation between **classification** and **action** is one of the
main architectural choices in the project.

------------------------------------------------------------------------

# 📚 2. Knowledge-Grounded Support

The AI should not answer support questions purely from its pretrained
knowledge.

Before generating a customer response, the system retrieves relevant
information from the project's support knowledge base.

Current knowledge areas include:

``` text
knowledge_base/
├── account_login.md
├── billing.md
├── security.md
└── assessment_issues.md
```

The retrieval layer includes query normalization and topic-aware scoring
so that different ways of expressing the same problem can map to the
appropriate knowledge source.

Examples:

``` text
"I was charged twice"
        ↓
billing / payment

"My account was hacked"
        ↓
security / unauthorized access

"I forgot my password"
        ↓
account / login

"The assessment crashed"
        ↓
assessment issues
```

## Retrieval Evaluation

The included retrieval evaluation currently reports:

``` text
Retrieval accuracy: 100.0%
Passed: 4/4
```

The four evaluated cases are:

  Scenario         Expected Knowledge Source   Result
  ---------------- --------------------------- --------
  Password Reset   `account_login.md`          PASS
  Billing          `billing.md`                PASS
  Security         `security.md`               PASS
  Assessment       `assessment_issues.md`      PASS

This is a **4-case retrieval evaluation**, not a claim of 100% accuracy
across all possible support tickets.

I am intentionally keeping that distinction explicit.

------------------------------------------------------------------------

# 🛡️ 3. Safe Resolution Gates

Retrieval alone does not mean the AI is allowed to respond.

The response generation layer applies explicit safety gates.

A grounded customer response is **not automatically generated** when:

-   The ticket is marked for escalation
-   The ticket is not AI-resolvable
-   Severity is `HIGH` or `CRITICAL`
-   Model confidence is below the configured threshold
-   Relevant knowledge-base context is unavailable

The current confidence threshold is configured at:

``` text
0.75
```

The philosophy is simple:

> **When the system is not sufficiently confident or the risk is high,
> escalation is preferable to a confident hallucination.**

------------------------------------------------------------------------

# 🚨 4. Human Escalation Workspace

When AI determines that a ticket should not be handled automatically, it
moves into the Human Escalations workspace.

The workspace is intentionally focused on what a support agent needs to
actually handle the customer.

It provides:

-   Escalation queue
-   Search and filters
-   Ticket and customer details
-   Original customer issue
-   Persistent conversation history
-   Support-agent message input
-   Send message
-   Ticket status
-   Mark as Done

The ticket lifecycle is:

``` text
ESCALATED
     ↓
HUMAN_ACTIVE
     ↓
DONE
```

The original customer issue is preserved as the initial conversation
message.

Agent messages are persisted, so the conversation does not disappear
when the dashboard is refreshed.

This is designed as a **human support workspace**, not another AI chat
interface.

------------------------------------------------------------------------

# 🔎 5. Investigation Centre

Some tickets need more than a simple handoff.

The Investigation Centre provides a deeper case-level view.

For a selected ticket, the support team can inspect:

### Case Overview

Customer and ticket information.

### Original Customer Issue

The exact issue submitted by the customer.

### AI Assessment

The AI's category, severity, confidence, resolvability, and escalation
decision.

### AI Customer Response

A grounded response can be generated for appropriate cases.

### Ask AI Investigator

The investigator can ask a question about the selected case.

### Findings

The investigator's analysis of the issue.

### Evidence

The ticket and existing AI analysis are used as supporting evidence.

### Recommendation

A suggested next action.

### Confidence

The investigator's confidence in its conclusion.

### Audit Trail

The operational history of the case is shown directly inside the
Investigation Centre.

This keeps the investigation workflow connected to the evidence and
history of the ticket.

------------------------------------------------------------------------

# 🕒 6. Auditability

AI decisions should not become a black box after the ticket is
processed.

The system records important operational events such as:

``` text
TICKET_RECEIVED
AI_ANALYSIS
KNOWLEDGE_RETRIEVED
RESOLUTION_DECISION
AI_INVESTIGATION
HUMAN_FEEDBACK
TICKET_CLOSED
```

Each event can contain:

-   Timestamp
-   Event type
-   Actor
-   Description
-   Relevant metadata

The dashboard formats that information for humans rather than exposing
raw internal JSON.

For example:

``` text
AI_ANALYSIS

Category: Password
Severity: LOW
Confidence: 97%
AI Resolvable: Yes
```

This makes it easier to answer:

> **What happened to this ticket, and why?**

------------------------------------------------------------------------

# 🧠 7. Continual Learning

A support system should not treat human intervention as the end of the
process.

Human corrections can become structured learning signals.

When an analyst reviews an AI decision, the system can record:

-   Feedback
-   Changed fields
-   AI prediction
-   Human correction
-   Learning example
-   Learning-cycle statistics

The feedback loop is:

``` text
AI PREDICTION
     ↓
HUMAN REVIEW
     ↓
CORRECTION
     ↓
VALIDATED LEARNING EXAMPLE
     ↓
LEARNING MEMORY
     ↓
FUTURE SIMILAR TICKETS
```

The current learning layer tracks metrics including:

-   Feedback count
-   Learning examples
-   Field corrections
-   Agreement rate
-   Category corrections
-   Severity corrections
-   Escalation corrections
-   Recent learning runs

The important design choice is that the system does **not blindly change
production behavior after every individual correction**.

Human feedback is captured as structured information that can be
evaluated and used in future learning cycles.

------------------------------------------------------------------------

# 🖥️ Dashboard

The dashboard is organized around the support workflow rather than
around individual AI features.

## Command Center

Provides the high-level operational view.

## 🚨 Human Escalations

Dedicated workspace for human agents handling escalated tickets.

## Ticket Queue

Provides the broader ticket-processing view.

## 🔎 Investigation

Deep case analysis, grounded response generation, investigation,
evidence, recommendations, and audit history.

## 🧠 Continual Learning

Human feedback, correction metrics, learning cycles, and recent learning
runs.

------------------------------------------------------------------------

# 🏗️ Architecture

The project is intentionally built as a modular local prototype.

``` text
                         ┌──────────────────────┐
                         │    Support Tickets   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      FastAPI         │
                         │    Backend/API       │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
              ┌──────────┐   ┌───────────┐   ┌───────────┐
              │ AI Triage│   │ RAG / KB  │   │ SQLite DB │
              └────┬─────┘   └─────┬─────┘   └───────────┘
                   │               │
                   └───────┬───────┘
                           ▼
                 ┌────────────────────┐
                 │ Resolution Decision│
                 └─────────┬──────────┘
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
          ┌─────────────┐     ┌──────────────┐
          │ Grounded AI │     │ Human Queue  │
          │    Reply    │     │ + Chat       │
          └─────────────┘     └──────┬───────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │ Investigation   │
                            │ + Audit Trail   │
                            └────────┬────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │ Continual       │
                            │ Learning        │
                            └─────────────────┘
```

------------------------------------------------------------------------

# 🧰 Technology Stack

  Layer              Technology
  ------------------ -------------------------
  Language           Python
  API                FastAPI
  Dashboard          Streamlit
  LLM Runtime        Ollama
  Model              `qwen3.5:4b`
  Database           SQLite
  Retrieval          Knowledge-base RAG
  Containerization   Docker / Docker Compose

The current application is designed to run locally.

That keeps the prototype inexpensive, reproducible, and easy to inspect
during evaluation.

------------------------------------------------------------------------

# 📁 Project Structure

``` text
support_agent/
│
├── app/
│   ├── config.py
│   ├── db.py
│   ├── learning.py
│   ├── ollama_client.py
│   └── reply.py
│
├── dashboard/
│   └── app.py
│
├── knowledge_base/
│   ├── account_login.md
│   ├── billing.md
│   ├── security.md
│   └── assessment_issues.md
│
├── scripts/
│   ├── evaluate_agent.py
│   └── ...
│
├── support_agent.db
├── docker-compose.yml
├── requirements.txt
└── README.md
```

> **Note:** If your submitted repository contains additional files, they
> can be added to this section. The structure above highlights the main
> application components.

------------------------------------------------------------------------

# ⚡ Getting Started

## 1. Clone the repository

``` bash
git clone <YOUR_REPOSITORY_URL>
cd support_agent
```

Replace `<YOUR_REPOSITORY_URL>` with the repository URL used for the
project repository.

## 2. Install dependencies

``` bash
pip install -r requirements.txt
```

## 2. Start Ollama

Make sure Ollama is running locally and the configured model is
available.

The application expects:

``` text
http://localhost:11434
```

The configured model is:

``` text
qwen3.5:4b
```

## 3. Start the API

Use the API command/configuration included in the repository.

The current local setup uses port:

``` text
8001
```

## 4. Start the dashboard

``` bash
streamlit run dashboard/app.py --server.port 8503
```

The dashboard will then be available locally.

------------------------------------------------------------------------

# 🧪 Running the Evaluation

The repository includes a retrieval evaluation script:

``` bash
python3 scripts/evaluate_agent.py
```

The current evaluation result is:

``` text
======================================================================
AI SUPPORT SENTINEL
RAG RETRIEVAL EVALUATION
======================================================================

[PASS] Password Reset
Expected: account_login.md

[PASS] Billing
Expected: billing.md

[PASS] Security
Expected: security.md

[PASS] Assessment
Expected: assessment_issues.md

======================================================================
Retrieval accuracy: 100.0%
Passed: 4/4
======================================================================
```

The evaluation is intentionally transparent about its scope.

It demonstrates that the current retrieval test cases resolve to the
expected knowledge-base documents. It should not be interpreted as a
universal benchmark for all support domains.

------------------------------------------------------------------------

# 🔐 Why Human-in-the-Loop Matters

One of the easiest ways to build an AI support demo is to make the AI
answer everything.

That is not how I wanted to approach this.

In support, some mistakes are cheap and some are expensive.

A slightly wrong answer about a general account question is different
from a wrong answer about:

-   security
-   billing
-   account compromise
-   high-severity incidents

So the system treats human escalation as a **designed capability**, not
a failure state.

The architecture makes room for humans at the points where judgment
matters most.

``` text
                 AI
                 │
        ┌────────┴────────┐
        │                 │
     Confident          Uncertain /
     + Low Risk          High Risk
        │                 │
        ▼                 ▼
   Auto Resolution     Human Review
        │                 │
        └────────┬────────┘
                 ▼
          Feedback / Learning
```

------------------------------------------------------------------------

# 📊 What Is Measured

The project currently has measurable checks for several parts of the
workflow.

### Retrieval

``` text
4 / 4 evaluated scenarios passed
100% retrieval accuracy on the included evaluation set
```

### Continual Learning

The learning layer tracks:

``` text
Feedback count
Learning examples
Field corrections
Agreement rate
Category corrections
Severity corrections
Escalation corrections
Learning runs
```

### Auditability

The system records operational events throughout the ticket lifecycle.

This makes it possible to inspect the path from:

``` text
Ticket received
      ↓
AI analysis
      ↓
Knowledge retrieval
      ↓
Resolution decision
      ↓
Investigation / human action
      ↓
Feedback
      ↓
Closure
```

------------------------------------------------------------------------

# ⚠️ Current Scope and Limitations

This is a hackathon-oriented prototype rather than a production support
platform.

A few things are intentionally lightweight:

### Local inference

Ollama is used for local LLM inference. A production deployment could
use hosted or self-managed model infrastructure.

### SQLite

SQLite is appropriate for a local prototype. A production system would
likely use a managed relational database.

### Retrieval

The current retrieval layer is lightweight and topic-aware. A production
implementation could add embeddings, hybrid retrieval, reranking, and
more extensive evaluation.

### Customer chat

The current persistent conversation is primarily the support-agent
workspace. A production version would connect it to a customer-facing
interface and real-time messaging infrastructure.

### Learning

Continual learning currently focuses on collecting and retrieving
validated human corrections. A production system would add formal
offline evaluation, model/version management, and controlled promotion
of improvements.

I consider these **next engineering steps**, not things to hide behind
the prototype.

------------------------------------------------------------------------

# 🔮 If I Took This to Production

My next priorities would be:

## 1. Stronger evaluation

Build a larger labeled dataset and measure:

-   Classification accuracy
-   Severity accuracy
-   Escalation precision/recall
-   Groundedness
-   Hallucination rate
-   Response quality
-   Investigation quality

## 2. Hybrid retrieval

Combine lexical retrieval with semantic embeddings and reranking.

## 3. Event-driven processing

Move ticket ingestion and processing toward an event-driven architecture
capable of handling continuous ticket streams.

## 4. Model routing

Use smaller models for simple tickets and stronger models for complex or
high-risk cases.

## 5. Production human workspace

Add role-based access, real-time customer-agent communication,
assignment, SLAs, notifications, and richer case management.

## 6. Controlled learning pipeline

Turn human corrections into versioned training/evaluation data and
promote improvements only after offline validation.

------------------------------------------------------------------------

# 💭 What I Learned Building It

The biggest lesson from this project was that **AI support is not
fundamentally a chatbot problem**.

The LLM is only one component.

The harder engineering problem is designing the system around it:

``` text
What should the AI know?
        ↓
What evidence should it use?
        ↓
How confident is it?
        ↓
What is the risk?
        ↓
Should it act?
        ↓
When should a human take over?
        ↓
What did the human change?
        ↓
How can the system learn from that?
```

That changed the way I thought about the challenge.

Instead of building:

> **"An AI that answers support tickets."**

I built:

> **"A support operations system that uses AI to make and explain
> operational decisions, while keeping humans in control when the system
> should not act alone."**

------------------------------------------------------------------------

# 🏁 Final Takeaway

AI Support Sentinel brings together:

**AI Triage**\
→ Understand the ticket.

**RAG**\
→ Ground decisions and responses in support knowledge.

**Risk Gates**\
→ Prevent unsafe automatic resolution.

**Human Escalation**\
→ Give support agents a focused workspace.

**Investigation**\
→ Help humans understand difficult cases.

**Audit Trail**\
→ Preserve what happened and why.

**Continual Learning**\
→ Turn human corrections into future learning signals.

The system is intentionally not built around the idea that **more
automation is always better**.

The goal is **better automation**:

``` text
Automate what is safe.
Escalate what is uncertain.
Explain what happened.
Learn from human judgment.
```

That's the direction I would take an AI support system beyond a basic
LLM demo.
