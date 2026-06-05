import streamlit as st
import json
import uuid
import datetime
from agent_core import SupportAgent

st.set_page_config(
    page_title="AI Customer Support Agent",
    page_icon="🤖",
    layout="wide"
)

st.markdown("""
<style>
.metric-box { background: #f8f9fa; border-radius: 10px; padding: 1rem; text-align: center; }
.ticket-card { background: white; border: 1px solid #eee; border-radius: 8px; padding: 12px; margin-bottom: 8px; }
.badge-open { background: #fee2e2; color: #dc2626; padding: 2px 8px; border-radius: 20px; font-size: 12px; }
.badge-resolved { background: #dcfce7; color: #16a34a; padding: 2px 8px; border-radius: 20px; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# ── Init ──────────────────────────────────────────────────────────────────────
if "agent" not in st.session_state:
    st.session_state.agent = SupportAgent()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "tickets" not in st.session_state:
    st.session_state.tickets = []

agent = st.session_state.agent

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🤖 SupportAI")
    st.caption("Built by Pr0_M1se 🚀")
    st.divider()

    # Business config
    st.subheader("Business Setup")
    biz_name = st.text_input("Business name", value="My Business")
    agent.business_name = biz_name

    uploaded_docs = st.file_uploader(
        "Upload company docs (PDF/TXT)",
        type=["pdf", "txt"],
        accept_multiple_files=True
    )
    if uploaded_docs:
        with st.spinner("Indexing documents..."):
            for doc in uploaded_docs:
                content = doc.read().decode("utf-8", errors="ignore")
                agent.add_document(doc.name, content)
        st.success(f"✅ {len(uploaded_docs)} document(s) indexed!")

    st.divider()

    # Stats
    resolved = len([t for t in st.session_state.tickets if t["status"] == "Resolved"])
    open_t = len([t for t in st.session_state.tickets if t["status"] == "Open"])
    st.metric("Open tickets", open_t)
    st.metric("Resolved today", resolved)
    st.metric("Messages handled", len(st.session_state.messages) // 2)

    st.divider()
    if st.button("🗑️ Clear chat"):
        st.session_state.messages = []
        st.rerun()

# ── Main tabs ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["💬 Chat", "🎫 Tickets", "📚 Docs"])

# ── TAB 1: Chat ───────────────────────────────────────────────────────────────
with tab1:
    st.subheader(f"Chat with {biz_name} Support")

    # Quick prompts
    col1, col2, col3, col4 = st.columns(4)
    prompts = [
        ("🔐 Reset password", "How do I reset my password?"),
        ("📦 Track order", "How can I track my order?"),
        ("💰 Refund", "I want to request a refund"),
        ("👤 Human agent", "I need to speak to a human agent"),
    ]
    for col, (label, prompt) in zip([col1, col2, col3, col4], prompts):
        if col.button(label, use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": prompt})

    # Chat history
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("ticket_id"):
                    st.caption(f"🎫 Ticket created: {msg['ticket_id']}")
                if msg.get("escalated"):
                    st.warning("⚠️ Escalated to human agent")

    # Input
    user_input = st.chat_input("Type your message here...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = agent.respond(user_input, st.session_state.messages)

            st.markdown(result["response"])

            msg_data = {"role": "assistant", "content": result["response"]}

            # Handle ticket creation
            if result.get("create_ticket"):
                ticket = {
                    "id": f"TKT-{str(uuid.uuid4())[:6].upper()}",
                    "issue": user_input,
                    "status": "Open",
                    "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "priority": result.get("priority", "Medium"),
                    "category": result.get("category", "General"),
                }
                st.session_state.tickets.append(ticket)
                st.caption(f"🎫 Ticket created: **{ticket['id']}**")
                msg_data["ticket_id"] = ticket["id"]

            # Handle escalation
            if result.get("escalate"):
                st.warning("⚠️ Connecting you to a human agent — avg wait: 3 mins")
                msg_data["escalated"] = True

        st.session_state.messages.append(msg_data)
        st.rerun()

# ── TAB 2: Tickets ────────────────────────────────────────────────────────────
with tab2:
    st.subheader("Support Tickets")

    col_a, col_b = st.columns([2, 1])
    with col_a:
        filter_status = st.selectbox("Filter", ["All", "Open", "In Progress", "Resolved"])
    with col_b:
        if st.button("➕ New ticket"):
            st.session_state.show_new_ticket = True

    # New ticket form
    if st.session_state.get("show_new_ticket"):
        with st.form("new_ticket_form"):
            st.subheader("Create ticket")
            name = st.text_input("Customer name")
            email = st.text_input("Email")
            category = st.selectbox("Category", ["Billing", "Technical", "Delivery", "Account", "Other"])
            priority = st.selectbox("Priority", ["Low", "Medium", "High", "Urgent"])
            issue = st.text_area("Issue description")
            submitted = st.form_submit_button("Create")
            if submitted and issue:
                ticket = {
                    "id": f"TKT-{str(uuid.uuid4())[:6].upper()}",
                    "customer": name,
                    "email": email,
                    "issue": issue,
                    "status": "Open",
                    "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "priority": priority,
                    "category": category,
                }
                st.session_state.tickets.append(ticket)
                st.session_state.show_new_ticket = False
                st.success(f"✅ Ticket {ticket['id']} created!")
                st.rerun()

    # Ticket list
    display = st.session_state.tickets
    if filter_status != "All":
        display = [t for t in display if t["status"] == filter_status]

    if not display:
        st.info("No tickets yet. They'll appear here when customers need help.")
    else:
        for ticket in display:
            with st.expander(f"**{ticket['id']}** — {ticket['issue'][:60]}..."):
                c1, c2, c3 = st.columns(3)
                c1.write(f"**Category:** {ticket.get('category','—')}")
                c2.write(f"**Priority:** {ticket.get('priority','—')}")
                c3.write(f"**Created:** {ticket.get('created','—')}")
                new_status = st.selectbox(
                    "Status",
                    ["Open", "In Progress", "Resolved"],
                    index=["Open", "In Progress", "Resolved"].index(ticket["status"]),
                    key=ticket["id"]
                )
                ticket["status"] = new_status
                if new_status == "Resolved" and st.button("✅ Mark resolved", key=f"res_{ticket['id']}"):
                    st.rerun()

# ── TAB 3: Docs ───────────────────────────────────────────────────────────────
with tab3:
    st.subheader("Knowledge Base")
    query = st.text_input("🔍 Search documentation", placeholder="e.g. refund policy, shipping, account settings")

    if query:
        with st.spinner("Searching..."):
            results = agent.search_docs(query)
        if results:
            for r in results:
                with st.expander(f"📄 {r['source']}"):
                    st.write(r["content"][:500] + "..." if len(r["content"]) > 500 else r["content"])
        else:
            st.info("No matching documents found. Upload docs in the sidebar to build your knowledge base.")
    else:
        docs = agent.list_docs()
        if docs:
            st.write(f"**{len(docs)} document(s) in knowledge base:**")
            for d in docs:
                st.write(f"📄 {d}")
        else:
            st.info("Upload company documents in the sidebar to get started.")
