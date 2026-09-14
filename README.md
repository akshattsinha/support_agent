# AI Support Sentinel v2.1

AI support operations command center with:
- 10,000+ support tickets
- AI triage and escalation
- RAG knowledge base
- Qwen 3.5 4B via Ollama
- AI case investigation
- Human-in-the-loop continual learning
- Validated learning memory for future tickets
- Feedback/evaluation dashboard
- Audit trail

## Ports
- FastAPI: `8001`
- Streamlit: `8503`
- Ollama: `11434`

## Run locally
```bash
cd support_agent_v2
source .venv/bin/activate
python3 -m uvicorn app.main:app --reload --port 8001
```

In another terminal:
```bash
cd support_agent_v2
source .venv/bin/activate
streamlit run dashboard/app.py --server.port 8503
```

## Ollama
The project is configured for the locally installed model:
```text
qwen3.5:4b
```

## Continual learning loop
1. AI classifies a ticket.
2. Analyst reviews the decision in the Investigation workspace.
3. Analyst submits corrected category, severity, and escalation decision.
4. The correction is stored in `feedback`.
5. A validated learning example is stored in `learning_examples`.
6. Similar validated examples are retrieved for future ticket triage/investigation.
7. `POST /learning/run` evaluates accumulated feedback and stores a learning-run snapshot.
8. The dashboard exposes feedback volume, corrections, agreement, and learning activity.

This implementation uses human-in-the-loop learning memory and periodic evaluation rather than fine-tuning the LLM after every ticket. It is designed to be extended later with a supervised classifier or LoRA/adapter training pipeline once enough validated examples accumulate.

## API endpoints
- `GET /health`
- `GET /tickets`
- `GET /tickets/{ticket_id}`
- `POST /tickets/process`
- `POST /tickets/{ticket_id}/investigate`
- `POST /tickets/{ticket_id}/feedback`
- `GET /learning/stats`
- `POST /learning/run`
