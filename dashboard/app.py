import streamlit as st
import requests
import pandas as pd

API = "http://localhost:8001"
CATEGORIES = ["Password", "Assessment", "Billing", "Security", "Technical", "Other", "Account"]

st.set_page_config(page_title="AI Support Sentinel", page_icon="🛡️", layout="wide")
st.title("🛡️ AI Support Sentinel")
st.caption("Support operations command center • AI triage • escalation intelligence • investigation • continual learning")

try:
    df = pd.DataFrame(requests.get(f"{API}/tickets", timeout=10).json())
except Exception:
    st.error("Start FastAPI first: python -m uvicorn app.main:app --reload --port 8001")
    st.stop()

if df.empty:
    st.warning("Seed the database first.")
    st.stop()

# -----------------------------------------------------------------------------
# COMMAND CENTER
# -----------------------------------------------------------------------------
t1, t2, t3, t4 = st.tabs(["Command Center", "Ticket Queue", "Investigation", "🧠 Continual Learning"])

with t1:
    a, b, c, d = st.columns(4)
    a.metric("TOTAL TICKETS", f"{len(df):,}")
    b.metric("ESCALATED", f"{(df.status == 'ESCALATED').sum():,}")
    c.metric("AI RESOLVED", f"{(df.status == 'AI_RESOLVED').sum():,}")
    d.metric("CRITICAL", f"{(df.severity == 'CRITICAL').sum():,}")

    l, r = st.columns(2)
    with l:
        st.subheader("Tickets by Category")
        st.bar_chart(df.category.value_counts())
    with r:
        st.subheader("Severity Distribution")
        st.bar_chart(df.severity.value_counts())

    st.subheader("🚨 Escalation Queue")
    q = df[df.status == "ESCALATED"].copy()
    q["confidence"] = q.confidence.map(lambda x: f"{x:.0%}")
    st.dataframe(q[["ticket_id", "category", "severity", "confidence", "team", "subject"]].head(25), use_container_width=True, hide_index=True)

    st.subheader("🧠 AI Signals")
    st.info(f"Assessment escalations: {(df.category == 'Assessment').sum():,} tickets total")
    st.info(f"Automatic-resolution rate: {(df.status == 'AI_RESOLVED').mean():.1%}")
    st.info(f"Critical cases requiring immediate attention: {(df.severity == 'CRITICAL').sum():,}")

# -----------------------------------------------------------------------------
# QUEUE
# -----------------------------------------------------------------------------
with t2:
    st.subheader("All Support Tickets")
    c1, c2, c3, c4 = st.columns(4)
    cf = c1.selectbox("Category", ["All"] + sorted(df.category.dropna().unique()))
    sf = c2.selectbox("Severity", ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"])
    tf = c3.selectbox("Status", ["All"] + sorted(df.status.dropna().unique()))
    search = c4.text_input("Search")
    x = df.copy()
    if cf != "All":
        x = x[x.category == cf]
    if sf != "All":
        x = x[x.severity == sf]
    if tf != "All":
        x = x[x.status == tf]
    if search:
        x = x[x.apply(lambda z: search.lower() in str(z).lower(), axis=1)]
    st.write(f"Showing **{len(x):,}** tickets")
    st.dataframe(x[["ticket_id", "subject", "category", "severity", "confidence", "status", "team"]], use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# INVESTIGATION + HUMAN FEEDBACK
# -----------------------------------------------------------------------------
with t3:
    st.subheader("🔎 AI Investigation Workspace")
    selected = st.selectbox("Select a case", df.ticket_id.tolist())
    detail = requests.get(f"{API}/tickets/{selected}", timeout=10).json()
    t = detail["ticket"]
    an = detail["analysis"]

    l, r = st.columns(2)
    with l:
        st.markdown(f"### {t['ticket_id']} — {t['subject']}")
        st.write(f"**Customer:** {t['customer_name']}")
        st.write(t["message"])
        st.write(f"**Status:** `{t['status']}`")
    with r:
        st.markdown("### AI Assessment")
        if an:
            st.write(f"**Category:** {an['category']}")
            st.write(f"**Severity:** `{an['severity']}`")
            st.write(f"**Sentiment:** {an['sentiment']}")
            st.write(f"**Confidence:** {an['confidence']:.0%}")
            st.write(f"**Escalate:** {'🚨 YES' if an['escalate'] else '✅ NO'}")
            st.write("**Why:**", an["escalation_reason"])
            st.write("**Recommended:**", an["recommended_action"])

    st.divider()
    q = st.text_input("Ask AI to investigate this case", placeholder="Why might this assessment have been submitted?")
    if st.button("Investigate", type="primary") and q:
        with st.spinner("Investigating..."):
            res = requests.post(f"{API}/tickets/{selected}/investigate", json={"question": q}, timeout=180)
        if res.ok:
            z = res.json()
            st.success(f"Confidence {z['confidence']:.0%}")
            st.markdown("**Findings**")
            st.write(z["findings"])
            st.markdown("**Evidence**")
            for e in z["evidence"]:
                st.write("•", e)
            st.markdown("**Recommendation**")
            st.write(z["recommendation"])
        else:
            st.error(res.text)

    st.divider()
    st.subheader("👤 Human Feedback")
    st.caption("Correct the AI assessment when necessary. Validated corrections become reusable learning examples for future cases.")
    if an:
        f1, f2, f3 = st.columns(3)
        with f1:
            human_category = st.selectbox("Correct category", sorted(set(CATEGORIES + [an["category"]])), index=sorted(set(CATEGORIES + [an["category"]])).index(an["category"]) if an["category"] in set(CATEGORIES + [an["category"]]) else 0)
        with f2:
            human_severity = st.selectbox("Correct severity", ["LOW", "MEDIUM", "HIGH", "CRITICAL"], index=["LOW", "MEDIUM", "HIGH", "CRITICAL"].index(an["severity"]))
        with f3:
            human_escalate = st.checkbox("Escalate", value=bool(an["escalate"]))
        reason = st.text_area("Why is this correction needed?", placeholder="Example: repeated login failures plus suspicious device pattern should be handled by Security.")
        analyst = st.text_input("Analyst", value="analyst")
        if st.button("Submit Feedback", type="secondary"):
            payload = {
                "human_category": human_category,
                "human_severity": human_severity,
                "human_escalate": human_escalate,
                "reason": reason,
                "analyst": analyst,
            }
            with st.spinner("Recording learning signal..."):
                rr = requests.post(f"{API}/tickets/{selected}/feedback", json=payload, timeout=20)
            if rr.ok:
                z = rr.json()
                st.success(f"Feedback stored • {z['corrections']} field correction(s) • learning example created")
            else:
                st.error(rr.text)

    st.divider()
    st.markdown("### 🕒 Audit Trail")
    for e in detail["audit"]:
        with st.expander(f"{e['timestamp']} · {e['event_type']}"):
            st.write(f"**Actor:** {e['actor']}")
            st.write(e["description"])
            if e["metadata"]:
                st.json(e["metadata"])

# -----------------------------------------------------------------------------
# CONTINUAL LEARNING
# -----------------------------------------------------------------------------
with t4:
    st.subheader("🧠 Continual Learning")
    st.caption("Human corrections are accumulated as validated learning memory and evaluated in periodic learning cycles.")

    try:
        stats = requests.get(f"{API}/learning/stats", timeout=10).json()
    except Exception as exc:
        st.error(f"Could not load learning metrics: {exc}")
        st.stop()

    a, b, c, d = st.columns(4)
    a.metric("HUMAN FEEDBACK", f"{stats['feedback_count']:,}")
    b.metric("LEARNING EXAMPLES", f"{stats['learning_examples']:,}")
    c.metric("FIELD CORRECTIONS", f"{stats['field_corrections']:,}")
    d.metric("DECISION AGREEMENT", f"{stats['agreement_rate']:.1%}")

    st.divider()
    l, r = st.columns(2)
    with l:
        st.markdown("### Correction Breakdown")
        breakdown = pd.DataFrame(
            {
                "Type": ["Category", "Severity", "Escalation"],
                "Corrections": [stats["category_corrections"], stats["severity_corrections"], stats["escalation_corrections"]],
            }
        ).set_index("Type")
        st.bar_chart(breakdown)
    with r:
        st.markdown("### Learning Activity")
        st.write(f"Feedback in last 7 days: **{stats['feedback_last_7_days']:,}**")
        st.write("Validated examples are automatically retrieved when processing new tickets.")
        if st.button("Run Learning Cycle", type="primary"):
            with st.spinner("Evaluating accumulated feedback..."):
                rr = requests.post(f"{API}/learning/run", timeout=30)
            if rr.ok:
                z = rr.json()
                st.success(f"Learning cycle #{z['run_id']} completed • agreement {z['agreement_rate']:.1%}")
                st.json(z)
            else:
                st.error(rr.text)

    st.divider()
    st.markdown("### Recent Learning Runs")
    if stats["recent_runs"]:
        runs = pd.DataFrame(stats["recent_runs"])
        runs["agreement_rate"] = runs["agreement_rate"].map(lambda x: f"{x:.1%}")
        st.dataframe(runs, use_container_width=True, hide_index=True)
    else:
        st.info("No learning cycles have been run yet. Submit a few human corrections, then run a cycle.")

    st.divider()
    st.markdown("### How the learning loop works")
    st.write("1. AI classifies the incoming ticket.")
    st.write("2. An analyst reviews and corrects category, severity, or escalation when needed.")
    st.write("3. The correction is stored as a validated learning example.")
    st.write("4. Similar validated examples are retrieved for future tickets and investigations.")
    st.write("5. A learning cycle measures agreement and exposes recurring error patterns.")
