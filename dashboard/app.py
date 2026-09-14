import streamlit as st
import requests
import pandas as pd

API = "http://localhost:8001"

CATEGORIES = [
    "Password",
    "Assessment",
    "Billing",
    "Security",
    "Technical",
    "Other",
    "Account",
]

SEVERITIES = [
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
]

st.set_page_config(
    page_title="AI Support Sentinel",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ AI Support Sentinel")
st.caption(
    "Support operations command center • AI triage • human escalation • "
    "investigation intelligence • continual learning"
)


# ============================================================
# LOAD TICKETS
# ============================================================

try:
    response = requests.get(
        f"{API}/tickets",
        timeout=10,
    )
    response.raise_for_status()
    df = pd.DataFrame(response.json())

except Exception:
    st.error(
        "Could not connect to FastAPI.\n\n"
        "Start the backend with:\n\n"
        "`python3 -m uvicorn app.main:app --reload --port 8001`"
    )
    st.stop()


if df.empty:
    st.warning("No tickets found. Seed the database first.")
    st.stop()


# ============================================================
# TABS
# ============================================================

t1, t2, t3, t4, t5 = st.tabs(
    [
        "Command Center",
        "🚨 Human Escalations",
        "Ticket Queue",
        "🔎 Investigation",
        "🧠 Continual Learning",
    ]
)


# ============================================================
# COMMAND CENTER
# ============================================================

with t1:

    st.subheader("Operations Command Center")

    total_tickets = len(df)

    escalated_count = (
        df["status"].isin(["ESCALATED", "HUMAN_ACTIVE"]).sum()
    )

    ai_resolved_count = (
        df["status"] == "AI_RESOLVED"
    ).sum()

    critical_count = (
        df["severity"] == "CRITICAL"
    ).sum()

    human_active_count = (
        df["status"] == "HUMAN_ACTIVE"
    ).sum()

    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

    a, b, c, d = st.columns(4)

    a.metric(
        "TOTAL TICKETS",
        f"{total_tickets:,}",
    )

    b.metric(
        "ESCALATED",
        f"{escalated_count:,}",
    )

    c.metric(
        "AI RESOLVED",
        f"{ai_resolved_count:,}",
    )

    d.metric(
        "CRITICAL",
        f"{critical_count:,}",
    )

    st.divider()

    # --------------------------------------------------------
    # CHARTS
    # --------------------------------------------------------

    left, right = st.columns(2)

    with left:

        st.subheader("Tickets by Category")

        category_counts = (
            df["category"]
            .value_counts()
        )

        st.bar_chart(category_counts)

    with right:

        st.subheader("Severity Distribution")

        severity_counts = (
            df["severity"]
            .value_counts()
            .reindex(SEVERITIES)
            .fillna(0)
        )

        st.bar_chart(severity_counts)

    st.divider()

    # --------------------------------------------------------
    # ESCALATION QUEUE
    # --------------------------------------------------------

    st.subheader("🚨 Escalation Queue")

    escalation_queue = df[
        df["status"].isin(
            ["ESCALATED", "HUMAN_ACTIVE"]
        )
    ].copy()

    if escalation_queue.empty:

        st.success(
            "No tickets are currently waiting for human support."
        )

    else:

        escalation_queue["confidence"] = (
            escalation_queue["confidence"]
            .map(lambda x: f"{x:.0%}")
        )

        st.dataframe(
            escalation_queue[
                [
                    "ticket_id",
                    "category",
                    "severity",
                    "confidence",
                    "status",
                    "team",
                    "subject",
                ]
            ].head(25),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    # --------------------------------------------------------
    # AI SIGNALS
    # --------------------------------------------------------

    st.subheader("🧠 AI Signals")

    col1, col2, col3 = st.columns(3)

    with col1:

        assessment_count = (
            df["category"] == "Assessment"
        ).sum()

        st.metric(
            "Assessment Tickets",
            f"{assessment_count:,}",
        )

    with col2:

        resolution_rate = (
            df["status"] == "AI_RESOLVED"
        ).mean()

        st.metric(
            "Automatic Resolution Rate",
            f"{resolution_rate:.1%}",
        )

    with col3:

        st.metric(
            "Human Active",
            f"{human_active_count:,}",
        )

    if critical_count > 0:

        st.warning(
            f"⚠️ {critical_count:,} critical case(s) "
            "require immediate attention."
        )


# ============================================================
# HUMAN ESCALATIONS
# ============================================================

with t2:

    st.subheader("🚨 Human Escalation Queue")

    st.caption(
        "Support agents handle escalated customers directly. "
        "Open a case, chat with the customer, resolve the issue, "
        "and mark the ticket as done."
    )

    # --------------------------------------------------------
    # LOAD ESCALATED TICKETS
    # --------------------------------------------------------

    try:

        escalation_response = requests.get(
            f"{API}/tickets/escalated",
            timeout=10,
        )

        escalation_response.raise_for_status()

        escalation_df = pd.DataFrame(
            escalation_response.json()
        )

    except Exception as exc:

        st.error(
            f"Could not load escalation queue: {exc}"
        )

        st.stop()

    if escalation_df.empty:

        st.success(
            "🎉 No active human escalations."
        )

    else:

        # ----------------------------------------------------
        # METRICS
        # ----------------------------------------------------

        open_count = (
            escalation_df["status"] == "ESCALATED"
        ).sum()

        human_active = (
            escalation_df["status"] == "HUMAN_ACTIVE"
        ).sum()

        critical = (
            escalation_df["severity"] == "CRITICAL"
        ).sum()

        high = (
            escalation_df["severity"] == "HIGH"
        ).sum()

        a, b, c, d = st.columns(4)

        a.metric(
            "OPEN ESCALATIONS",
            f"{open_count:,}",
        )

        b.metric(
            "HUMAN ACTIVE",
            f"{human_active:,}",
        )

        c.metric(
            "CRITICAL",
            f"{critical:,}",
        )

        d.metric(
            "HIGH",
            f"{high:,}",
        )

        st.divider()

        # ----------------------------------------------------
        # FILTERS
        # ----------------------------------------------------

        f1, f2, f3 = st.columns(3)

        with f1:

            severity_filter = st.selectbox(
                "Severity",
                [
                    "All",
                    "CRITICAL",
                    "HIGH",
                    "MEDIUM",
                    "LOW",
                ],
                key="human_severity_filter",
            )

        with f2:

            team_filter = st.selectbox(
                "Team",
                [
                    "All"
                ]
                + sorted(
                    escalation_df[
                        "team"
                    ]
                    .dropna()
                    .unique()
                    .tolist()
                ),
                key="human_team_filter",
            )

        with f3:

            search = st.text_input(
                "Search customer / ticket",
                key="human_search",
            )

        filtered = escalation_df.copy()

        if severity_filter != "All":

            filtered = filtered[
                filtered["severity"]
                == severity_filter
            ]

        if team_filter != "All":

            filtered = filtered[
                filtered["team"]
                == team_filter
            ]

        if search:

            search_lower = search.lower()

            filtered = filtered[
                filtered.apply(
                    lambda row:
                    search_lower
                    in str(row.to_dict()).lower(),
                    axis=1,
                )
            ]

        st.write(
            f"Showing **{len(filtered):,}** active escalation(s)"
        )

        if filtered.empty:

            st.info(
                "No escalations match your filters."
            )

        else:

            # ------------------------------------------------
            # TICKET SELECTOR
            # ------------------------------------------------

            ticket_options = (
                filtered["ticket_id"]
                .tolist()
            )

            selected_ticket = st.selectbox(
                "Select escalation",
                ticket_options,
                key="selected_human_ticket",
            )

            # ------------------------------------------------
            # LOAD TICKET
            # ------------------------------------------------

            try:

                detail_response = requests.get(
                    f"{API}/tickets/{selected_ticket}",
                    timeout=10,
                )

                detail_response.raise_for_status()

                detail = detail_response.json()

            except Exception as exc:

                st.error(
                    f"Could not load ticket: {exc}"
                )

                st.stop()

            ticket = detail["ticket"]

            st.divider()

            # ------------------------------------------------
            # CUSTOMER / ISSUE
            # ------------------------------------------------

            left, right = st.columns(
                [1, 1.4]
            )

            with left:

                st.markdown(
                    "### 👤 Customer"
                )

                st.markdown(
                    f"**{ticket['customer_name']}**"
                )

                st.write(
                    f"**Ticket:** `{ticket['ticket_id']}`"
                )

                st.write(
                    f"**Category:** `{ticket['category']}`"
                )

                st.write(
                    f"**Severity:** `{ticket['severity']}`"
                )

                st.write(
                    f"**Team:** `{ticket['team']}`"
                )

                status = ticket["status"]

                if status == "ESCALATED":

                    st.warning(
                        "🚨 Waiting for human support"
                    )

                elif status == "HUMAN_ACTIVE":

                    st.info(
                        "🟢 Support agent is handling this case"
                    )

                elif status == "DONE":

                    st.success(
                        "✅ Ticket resolved"
                    )

                st.divider()

                st.markdown(
                    "### 📝 Original Customer Issue"
                )

                st.write(
                    ticket["message"]
                )

            # ------------------------------------------------
            # SUPPORT CHAT
            # ------------------------------------------------

            with right:

                st.markdown(
                    "### 💬 Customer Support Chat"
                )

                st.caption(
                    "Communicate directly with the customer "
                    "to understand and resolve the issue."
                )

                # --------------------------------------------
                # LOAD MESSAGES
                # --------------------------------------------

                try:

                    messages_response = requests.get(
                        f"{API}/tickets/"
                        f"{selected_ticket}/messages",
                        timeout=10,
                    )

                    messages_response.raise_for_status()

                    messages = (
                        messages_response
                        .json()
                    )

                except Exception as exc:

                    st.error(
                        f"Could not load chat: {exc}"
                    )

                    messages = []

                # --------------------------------------------
                # CHAT WINDOW
                # --------------------------------------------

                chat_container = st.container(
                    height=450,
                    border=True,
                )

                with chat_container:

                    if not messages:

                        st.info(
                            "No messages yet."
                        )

                    else:

                        for message in messages:

                            sender = (
                                message.get(
                                    "sender",
                                    "unknown",
                                )
                            )

                            text = (
                                message.get(
                                    "message",
                                    "",
                                )
                            )

                            if sender == "customer":

                                with st.chat_message(
                                    "user"
                                ):

                                    st.markdown(
                                        "**Customer**"
                                    )

                                    st.write(
                                        text
                                    )

                            else:

                                with st.chat_message(
                                    "assistant"
                                ):

                                    st.markdown(
                                        "**Support Agent**"
                                    )

                                    st.write(
                                        text
                                    )

                # --------------------------------------------
                # SEND MESSAGE
                # --------------------------------------------

                st.markdown(
                    "#### Reply to customer"
                )

                agent_name = st.text_input(
                    "Support agent",
                    value="support_agent",
                    key=f"agent_name_{selected_ticket}",
                )

                message_text = st.text_area(
                    "Message",
                    placeholder=(
                        "Type your response to the customer..."
                    ),
                    key=f"message_{selected_ticket}",
                    height=100,
                )

                send_col, close_col = st.columns(
                    [1, 1]
                )

                with send_col:

                    send_clicked = st.button(
                        "📨 Send Message",
                        type="primary",
                        use_container_width=True,
                        key=f"send_{selected_ticket}",
                    )

                with close_col:

                    close_clicked = st.button(
                        "✅ Mark as Done",
                        use_container_width=True,
                        key=f"close_{selected_ticket}",
                    )

                # --------------------------------------------
                # SEND MESSAGE
                # --------------------------------------------

                if send_clicked:

                    if status == "DONE":

                        st.error(
                            "This ticket is already closed."
                        )

                    elif not message_text.strip():

                        st.warning(
                            "Please enter a message."
                        )

                    else:

                        try:

                            send_response = requests.post(
                                f"{API}/tickets/"
                                f"{selected_ticket}/messages",
                                json={
                                    "message":
                                        message_text.strip(),
                                    "agent":
                                        agent_name.strip()
                                        or "support_agent",
                                },
                                timeout=20,
                            )

                            if send_response.ok:

                                st.success(
                                    "Message sent."
                                )

                                st.rerun()

                            else:

                                st.error(
                                    send_response.text
                                )

                        except Exception as exc:

                            st.error(
                                f"Could not send message: {exc}"
                            )

                # --------------------------------------------
                # CLOSE TICKET
                # --------------------------------------------

                if close_clicked:

                    if status == "DONE":

                        st.info(
                            "Ticket is already marked as done."
                        )

                    else:

                        try:

                            close_response = requests.post(
                                f"{API}/tickets/"
                                f"{selected_ticket}/close",
                                timeout=20,
                            )

                            if close_response.ok:

                                st.success(
                                    "Ticket marked as done."
                                )

                                st.rerun()

                            else:

                                st.error(
                                    close_response.text
                                )

                        except Exception as exc:

                            st.error(
                                f"Could not close ticket: {exc}"
                            )


# ============================================================
# TICKET QUEUE
# ============================================================

with t3:

    st.subheader("All Support Tickets")

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        category_filter = st.selectbox(
            "Category",
            [
                "All"
            ]
            + sorted(
                df["category"]
                .dropna()
                .unique()
                .tolist()
            ),
            key="ticket_category_filter",
        )

    with c2:

        severity_filter = st.selectbox(
            "Severity",
            [
                "All",
                "CRITICAL",
                "HIGH",
                "MEDIUM",
                "LOW",
            ],
            key="ticket_severity_filter",
        )

    with c3:

        status_filter = st.selectbox(
            "Status",
            [
                "All"
            ]
            + sorted(
                df["status"]
                .dropna()
                .unique()
                .tolist()
            ),
            key="ticket_status_filter",
        )

    with c4:

        ticket_search = st.text_input(
            "Search",
            key="ticket_search",
        )

    filtered_df = df.copy()

    if category_filter != "All":

        filtered_df = filtered_df[
            filtered_df["category"]
            == category_filter
        ]

    if severity_filter != "All":

        filtered_df = filtered_df[
            filtered_df["severity"]
            == severity_filter
        ]

    if status_filter != "All":

        filtered_df = filtered_df[
            filtered_df["status"]
            == status_filter
        ]

    if ticket_search:

        search_lower = (
            ticket_search.lower()
        )

        filtered_df = filtered_df[
            filtered_df.apply(
                lambda row:
                search_lower
                in str(row.to_dict()).lower(),
                axis=1,
            )
        ]

    st.write(
        f"Showing **{len(filtered_df):,}** tickets"
    )

    st.dataframe(
        filtered_df[
            [
                "ticket_id",
                "subject",
                "category",
                "severity",
                "confidence",
                "status",
                "team",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# AI INVESTIGATION
# ============================================================

with t4:

    st.subheader(
        "🔎 AI Investigation Workspace"
    )

    st.caption(
        "Use the AI investigator to analyze difficult cases "
        "and ask questions using the ticket, knowledge base, "
        "and validated learning examples."
    )

    selected = st.selectbox(
        "Select a case",
        df.ticket_id.tolist(),
        key="investigation_ticket",
    )

    try:

        detail_response = requests.get(
            f"{API}/tickets/{selected}",
            timeout=10,
        )

        detail_response.raise_for_status()

        detail = detail_response.json()

    except Exception as exc:

        st.error(
            f"Could not load ticket: {exc}"
        )

        st.stop()

    ticket = detail["ticket"]

    analysis = detail["analysis"]

    left, right = st.columns(2)

    # ============================================================
# AI CUSTOMER REPLY
    # ============================================================

    st.divider()

    st.markdown(
        "### 💬 AI Customer Response"
    )

    if analysis:

        ai_resolvable = bool(
            analysis.get(
                "ai_resolvable",
                False,
            )
        )

        escalate = bool(
            analysis.get(
                "escalate",
                False,
            )
        )

        if escalate:

            st.warning(
                "🚨 This ticket requires human review. "
                "AI will not automatically reply."
            )

        elif not ai_resolvable:

            st.warning(
                "⚠️ AI could not safely resolve this "
                "ticket from the available knowledge."
            )

        else:

            st.caption(
                "Generate a customer-facing response "
                "grounded in the support knowledge base."
            )

            if st.button(
                "✨ Generate Grounded Reply",
                type="primary",
                key=f"generate_reply_{selected}",
            ):

                with st.spinner(
                    "Generating grounded customer response..."
                ):

                    try:

                        reply_response = requests.post(
                            f"{API}/tickets/"
                            f"{selected}/reply",
                            timeout=180,
                        )

                        if reply_response.ok:

                            reply_result = (
                                reply_response.json()
                            )

                            if reply_result.get(
                                "can_reply",
                                False,
                            ):

                                st.success(
                                    "Grounded response generated."
                                )

                                st.markdown(
                                    "#### Suggested Customer Reply"
                                )

                                st.chat_message(
                                    "assistant"
                                ).write(
                                    reply_result[
                                        "reply"
                                    ]
                                )

                                sources = (
                                    reply_result.get(
                                        "sources",
                                        [],
                                    )
                                )

                                if sources:

                                    st.markdown(
                                        "#### Knowledge Sources"
                                    )

                                    for source in sources:

                                        st.write(
                                            f"📚 `{source}`"
                                        )

                                st.caption(
                                    "Reply confidence: "
                                    f"{reply_result.get('confidence', 0):.0%}"
                                )

                            else:

                                st.warning(
                                    reply_result.get(
                                        "reason",
                                        "AI could not safely "
                                        "generate a response.",
                                    )
                                )

                        else:

                            st.error(
                                reply_response.text
                            )

                    except Exception as exc:

                        st.error(
                            f"Reply generation failed: {exc}"
                        )

    else:

        st.info(
            "Run AI analysis before generating "
            "a customer response."
        )

        # --------------------------------------------------------
    # TICKET
    # --------------------------------------------------------

    with left:

        st.markdown(
            f"### {ticket['ticket_id']} — "
            f"{ticket['subject']}"
        )

        st.write(
            f"**Customer:** "
            f"{ticket['customer_name']}"
        )

        st.write(
            ticket["message"]
        )

        st.write(
            f"**Status:** `{ticket['status']}`"
        )

        st.write(
            f"**Team:** `{ticket['team']}`"
        )

    # --------------------------------------------------------
    # AI ASSESSMENT
    # --------------------------------------------------------

    with right:

        st.markdown(
            "### AI Assessment"
        )

        if analysis:

            st.write(
                f"**Category:** "
                f"{analysis['category']}"
            )

            st.write(
                f"**Severity:** "
                f"`{analysis['severity']}`"
            )

            st.write(
                f"**Sentiment:** "
                f"{analysis['sentiment']}"
            )

            st.write(
                f"**Confidence:** "
                f"{analysis['confidence']:.0%}"
            )

            escalate_text = (
                "🚨 YES"
                if analysis["escalate"]
                else "✅ NO"
            )

            st.write(
                f"**Escalate:** "
                f"{escalate_text}"
            )

            st.write(
                "**Why:**",
                analysis[
                    "escalation_reason"
                ],
            )

            st.write(
                "**Recommended:**",
                analysis[
                    "recommended_action"
                ],
            )

        else:

            st.info(
                "No AI analysis available."
            )

    # --------------------------------------------------------
    # ASK AI
    # --------------------------------------------------------

    st.divider()

    st.markdown(
        "### 🤖 Ask AI Investigator"
    )

    question = st.text_input(
        "Ask a question about this case",
        placeholder=(
            "Why might this assessment "
            "have been submitted?"
        ),
        key="investigation_question",
    )

    if st.button(
        "Investigate",
        type="primary",
        key="investigate_button",
    ) and question:

        with st.spinner(
            "AI is investigating the case..."
        ):

            try:

                investigation_response = requests.post(
                    f"{API}/tickets/"
                    f"{selected}/investigate",
                    json={
                        "question": question
                    },
                    timeout=180,
                )

                if investigation_response.ok:

                    result = (
                        investigation_response
                        .json()
                    )

                    st.success(
                        "Investigation completed."
                    )

                    st.write(
                        f"**Confidence:** "
                        f"{result['confidence']:.0%}"
                    )

                    st.markdown(
                        "#### Findings"
                    )

                    st.write(
                        result["findings"]
                    )

                    st.markdown(
                        "#### Evidence"
                    )

                    evidence = (
                        result.get(
                            "evidence",
                            [],
                        )
                    )

                    if evidence:

                        for item in evidence:

                            st.write(
                                "•",
                                item,
                            )

                    else:

                        st.info(
                            "No supporting evidence found."
                        )

                    st.markdown(
                        "#### Recommendation"
                    )

                    st.write(
                        result[
                            "recommendation"
                        ]
                    )

                else:

                    st.error(
                        investigation_response.text
                    )

            except Exception as exc:

                st.error(
                    f"Investigation failed: {exc}"
                )




    # --------------------------------------------------------
    # AUDIT TRAIL
    # --------------------------------------------------------
    st.divider()

    st.subheader("🕒 Audit Trail")
    st.caption(
        "Operational history of AI decisions, human actions, "
        "investigations, and ticket lifecycle events."
    )

    audit_events = detail.get("audit", [])

    if not audit_events:
        st.info("No audit events available for this ticket.")
    else:
        st.write(f"Showing **{len(audit_events):,}** audit event(s)")

        def _format_audit_value(value):
            """Render audit metadata as readable UI instead of raw JSON."""
            if isinstance(value, bool):
                return "Yes" if value else "No"
            if value is None:
                return "—"
            if isinstance(value, float):
                return f"{value:.2f}"
            return str(value)

        def _render_audit_metadata(metadata):
            if not metadata:
                return

            if isinstance(metadata, dict):
                for key, value in metadata.items():
                    label = str(key).replace("_", " ").strip().title()

                    if isinstance(value, list):
                        st.markdown(f"**{label}**")
                        for item in value:
                            st.markdown(
                                f"- {_format_audit_value(item)}"
                            )
                    elif isinstance(value, dict):
                        st.markdown(f"**{label}**")
                        for nested_key, nested_value in value.items():
                            nested_label = (
                                str(nested_key)
                                .replace("_", " ")
                                .strip()
                                .title()
                            )
                            st.write(
                                f"**{nested_label}:** "
                                f"{_format_audit_value(nested_value)}"
                            )
                    else:
                        st.write(
                            f"**{label}:** "
                            f"{_format_audit_value(value)}"
                        )
            elif isinstance(metadata, list):
                for item in metadata:
                    st.markdown(
                        f"- {_format_audit_value(item)}"
                    )
            else:
                st.write(_format_audit_value(metadata))

        for event in audit_events:
            event_type = event.get("event_type", "UNKNOWN")
            timestamp = event.get("timestamp", "")
            actor = event.get("actor", "unknown")
            description = event.get("description", "")
            metadata = event.get("metadata")

            with st.expander(
                f"{timestamp} · {event_type}",
                expanded=False,
            ):
                st.write(f"**Actor:** {actor}")

                if description:
                    st.write(description)

                if metadata:
                    st.markdown("**Event Details**")
                    _render_audit_metadata(metadata)

# ============================================================
# CONTINUAL LEARNING
# ============================================================

with t5:

    st.subheader(
        "🧠 Continual Learning"
    )

    st.caption(
        "Human corrections are accumulated as validated "
        "learning memory. Similar examples are retrieved "
        "when processing future tickets."
    )

    # --------------------------------------------------------
    # HUMAN FEEDBACK
    # --------------------------------------------------------

    st.divider()

    st.subheader(
        "👤 Human Feedback"
    )

    st.caption(
        "Review and correct AI decisions. Validated corrections "
        "become reusable learning examples for future tickets."
    )

    feedback_ticket = st.selectbox(
        "Select a ticket to review",
        df.ticket_id.tolist(),
        key="feedback_ticket",
    )

    try:
        feedback_detail_response = requests.get(
            f"{API}/tickets/{feedback_ticket}",
            timeout=10,
        )

        feedback_detail_response.raise_for_status()

        feedback_detail = feedback_detail_response.json()

        feedback_analysis = feedback_detail.get(
            "analysis"
        )

    except Exception as exc:
        st.error(
            f"Could not load ticket for feedback: {exc}"
        )
        feedback_analysis = None

    if feedback_analysis:

        st.markdown(
            f"**Ticket:** `{feedback_ticket}`"
        )

        f1, f2, f3 = st.columns(3)

        available_categories = sorted(
            set(
                CATEGORIES
                + [feedback_analysis["category"]]
            )
        )

        with f1:

            default_category_index = (
                available_categories.index(
                    feedback_analysis["category"]
                )
                if feedback_analysis["category"]
                in available_categories
                else 0
            )

            human_category = st.selectbox(
                "Correct category",
                available_categories,
                index=default_category_index,
                key=f"feedback_category_{feedback_ticket}",
            )

        with f2:

            current_severity = feedback_analysis.get(
                "severity",
                "MEDIUM",
            )

            severity_index = (
                SEVERITIES.index(current_severity)
                if current_severity in SEVERITIES
                else 0
            )

            human_severity = st.selectbox(
                "Correct severity",
                SEVERITIES,
                index=severity_index,
                key=f"feedback_severity_{feedback_ticket}",
            )

        with f3:

            human_escalate = st.checkbox(
                "Escalate",
                value=bool(
                    feedback_analysis.get(
                        "escalate",
                        False,
                    )
                ),
                key=f"feedback_escalate_{feedback_ticket}",
            )

        reason = st.text_area(
            "Why is this correction needed?",
            placeholder=(
                "Explain why the AI decision should be corrected."
            ),
            key=f"feedback_reason_{feedback_ticket}",
        )

        analyst = st.text_input(
            "Analyst",
            value="analyst",
            key=f"feedback_analyst_{feedback_ticket}",
        )

        if st.button(
            "Submit Feedback",
            type="primary",
            key=f"submit_feedback_{feedback_ticket}",
        ):

            payload = {
                "human_category": human_category,
                "human_severity": human_severity,
                "human_escalate": human_escalate,
                "reason": reason,
                "analyst": analyst,
            }

            with st.spinner(
                "Recording learning signal..."
            ):

                try:

                    feedback_response = requests.post(
                        f"{API}/tickets/"
                        f"{feedback_ticket}/feedback",
                        json=payload,
                        timeout=20,
                    )

                    if feedback_response.ok:

                        result = feedback_response.json()

                        st.success(
                            "Feedback stored • "
                            f"{result['corrections']} "
                            "field correction(s) • "
                            "learning example created"
                        )

                        st.rerun()

                    else:

                        st.error(
                            feedback_response.text
                        )

                except Exception as exc:

                    st.error(
                        f"Could not submit feedback: {exc}"
                    )

    # --------------------------------------------------------
    # LOAD LEARNING STATS
    # --------------------------------------------------------

    try:

        learning_response = requests.get(
            f"{API}/learning/stats",
            timeout=10,
        )

        learning_response.raise_for_status()

        stats = learning_response.json()

    except Exception as exc:

        st.error(
            f"Could not load learning metrics: {exc}"
        )

        st.stop()

    # --------------------------------------------------------
    # TOP METRICS
    # --------------------------------------------------------

    a, b, c, d = st.columns(4)

    a.metric(
        "HUMAN FEEDBACK",
        f"{stats['feedback_count']:,}",
    )

    b.metric(
        "LEARNING EXAMPLES",
        f"{stats['learning_examples']:,}",
    )

    c.metric(
        "FIELD CORRECTIONS",
        f"{stats['field_corrections']:,}",
    )

    d.metric(
        "DECISION AGREEMENT",
        f"{stats['agreement_rate']:.1%}",
    )

    st.divider()

    # --------------------------------------------------------
    # CORRECTION BREAKDOWN
    # --------------------------------------------------------

    left, right = st.columns(2)

    with left:

        st.markdown(
            "### Correction Breakdown"
        )

        breakdown = pd.DataFrame(
            {
                "Type": [
                    "Category",
                    "Severity",
                    "Escalation",
                ],
                "Corrections": [
                    stats[
                        "category_corrections"
                    ],
                    stats[
                        "severity_corrections"
                    ],
                    stats[
                        "escalation_corrections"
                    ],
                ],
            }
        ).set_index("Type")

        st.bar_chart(
            breakdown
        )

    # --------------------------------------------------------
    # LEARNING ACTIVITY
    # --------------------------------------------------------

    with right:

        st.markdown(
            "### Learning Activity"
        )

        st.write(
            "Feedback in last 7 days: "
            f"**{stats['feedback_last_7_days']:,}**"
        )

        st.write(
            "Validated examples are automatically "
            "retrieved when processing new tickets."
        )

        st.info(
            "The current learning system uses validated "
            "human corrections as decision guidance for "
            "future tickets."
        )

        if st.button(
            "Run Learning Cycle",
            type="primary",
            key="run_learning_cycle",
        ):

            with st.spinner(
                "Evaluating accumulated feedback..."
            ):

                try:

                    learning_run_response = requests.post(
                        f"{API}/learning/run",
                        timeout=30,
                    )

                    if learning_run_response.ok:

                        result = (
                            learning_run_response
                            .json()
                        )

                        st.success(
                            "Learning cycle "
                            f"#{result['run_id']} "
                            "completed successfully."
                        )

                        # ------------------------------------
                        # RESULTS
                        # ------------------------------------

                        r1, r2, r3, r4 = st.columns(4)

                        r1.metric(
                            "FEEDBACK REVIEWED",
                            f"{result['feedback_count']:,}",
                        )

                        r2.metric(
                            "LEARNING EXAMPLES",
                            f"{result['learning_examples']:,}",
                        )

                        r3.metric(
                            "FIELD CORRECTIONS",
                            f"{result['field_corrections']:,}",
                        )

                        r4.metric(
                            "DECISION AGREEMENT",
                            f"{result['agreement_rate']:.1%}",
                        )

                        st.divider()

                        # ------------------------------------
                        # INSIGHTS
                        # ------------------------------------

                        st.markdown(
                            "### Learning Insights"
                        )

                        insight_left, insight_right = (
                            st.columns(2)
                        )

                        with insight_left:

                            st.markdown(
                                "**Severity Corrections**"
                            )

                            severity_corrections = (
                                result.get(
                                    "top_severity_corrections",
                                    [],
                                )
                            )

                            if severity_corrections:

                                for correction, count in (
                                    severity_corrections
                                ):

                                    st.write(
                                        f"• `{correction}` "
                                        f"— **{count}**"
                                    )

                            else:

                                st.write(
                                    "No severity corrections."
                                )

                            st.markdown(
                                "**Category Corrections**"
                            )

                            category_corrections = (
                                result.get(
                                    "top_category_corrections",
                                    [],
                                )
                            )

                            if category_corrections:

                                for correction, count in (
                                    category_corrections
                                ):

                                    st.write(
                                        f"• `{correction}` "
                                        f"— **{count}**"
                                    )

                            else:

                                st.write(
                                    "No category corrections."
                                )

                        with insight_right:

                            st.markdown(
                                "**Escalation Corrections**"
                            )

                            escalation_corrections = (
                                result[
                                    "escalation_corrections"
                                ]
                            )

                            st.write(
                                f"• **{escalation_corrections}** "
                                "escalation decision(s) "
                                "corrected by humans."
                            )

                            st.markdown(
                                "**What the system learned**"
                            )

                            if (
                                result[
                                    "field_corrections"
                                ]
                                > 0
                            ):

                                st.info(
                                    "Human corrections have "
                                    "been converted into "
                                    "validated learning "
                                    "examples. Similar future "
                                    "tickets will use these "
                                    "examples as decision "
                                    "guidance."
                                )

                            else:

                                st.success(
                                    "The AI agreed with all "
                                    "reviewed human decisions."
                                )

                    else:

                        st.error(
                            learning_run_response.text
                        )

                except Exception as exc:

                    st.error(
                        f"Learning cycle failed: {exc}"
                    )

    st.divider()

    # ========================================================
    # RECENT LEARNING RUNS
    # ========================================================

    st.markdown(
        "### Recent Learning Runs"
    )

    recent_runs = stats.get(
        "recent_runs",
        [],
    )

    if recent_runs:

        runs_df = pd.DataFrame(
            recent_runs
        )

        if "agreement_rate" in runs_df.columns:

            runs_df[
                "agreement_rate"
            ] = runs_df[
                "agreement_rate"
            ].map(
                lambda x:
                f"{x:.1%}"
            )

        st.dataframe(
            runs_df,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No learning cycles have been run yet. "
            "Submit a few human corrections, then run "
            "a cycle."
        )

    st.divider()

    # ========================================================
    # HOW IT WORKS
    # ========================================================

    st.markdown(
        "### How the Learning Loop Works"
    )

    learning_steps = [
        (
            "1",
            "AI classifies the incoming ticket.",
        ),
        (
            "2",
            "A support analyst reviews the AI decision.",
        ),
        (
            "3",
            "The analyst corrects category, severity, "
            "or escalation when necessary.",
        ),
        (
            "4",
            "The correction is stored as a validated "
            "learning example.",
        ),
        (
            "5",
            "Similar validated examples are retrieved "
            "for future tickets.",
        ),
        (
            "6",
            "Learning cycles measure AI-human agreement "
            "and recurring error patterns.",
        ),
    ]

    for number, description in learning_steps:

        st.write(
            f"**{number}.** {description}"
        )
