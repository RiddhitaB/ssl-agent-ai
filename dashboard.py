import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from langchain_community.callbacks import StreamlitCallbackHandler
import subprocess
import sys
import os
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from decision_agent import run_decision_logic

st.set_page_config(layout="wide")

# ---------- CUSTOM CSS FOR SAAS LOOK ----------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #1e1b4b 0%, #14113a 100%);
}

section[data-testid="stSidebar"] {
    background-color: #1c1a55;
}

div[data-testid="stMetric"] {
    background-color: #26247a;
    border-radius: 18px;
    padding: 1.6rem;
    border: 1px solid rgba(255,255,255,0.05);
    box-shadow: 0 8px 30px rgba(0,0,0,0.25);
}

.stDataFrame {
    background-color: #26247a;
    border-radius: 18px;
    padding: 1rem;
}

.stButton>button {
    background: linear-gradient(90deg, #06b6d4, #3b82f6);
    border-radius: 14px;
    padding: 0.6rem 1.2rem;
    font-weight: 600;
}

h1, h2, h3 {
    font-weight: 600;
    letter-spacing: 0.5px;
}
</style>
""", unsafe_allow_html=True)

# ---------- LOAD SCANNER DATA ----------
def load_data():
    try:
        df = pd.read_csv("tls_certificate_scan_history.csv")
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        latest = df.sort_values("timestamp").groupby("domain").tail(1)
        return latest
    except:
        return pd.DataFrame()

# ---------- LOAD AI DECISIONS ----------
def load_agent_decisions():
    try:
        return pd.read_csv("tls_agent_decisions.csv")
    except:
        return pd.DataFrame()

df = load_data()
decisions_df = load_agent_decisions()

# auto refresh every 60 sec
st_autorefresh(interval=60000, key="refresh")

# ---------- SIDEBAR ----------
with st.sidebar:
    st.title("TLS Monitor")
    page = st.radio("Navigation", ["Dashboard", "Inventory", "Operations"])
    st.caption("Last refresh: " + datetime.utcnow().strftime("%H:%M:%S UTC"))

# =====================================================
# ================= DASHBOARD ==========================
# =====================================================
if page == "Dashboard":

    st.title("Infrastructure Analytics")

    if df.empty:
        st.warning("No scan data available.")
        st.stop()

    total = len(df)
    critical = len(df[df["risk_level"] == "CRITICAL"])
    avg_days = int(df["days_left"].mean())
    compliance = round(((total - critical)/total)*100, 1)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Managed Assets", total)
    c2.metric("Critical Certificates", critical)
    c3.metric("Average Days Remaining", avg_days)
    c4.metric("Compliance %", compliance)

    st.markdown("")

    colA, colB = st.columns([2, 1])

    with colA:
        fig = px.bar(
            df.sort_values("days_left").head(10),
            x="days_left",
            y="domain",
            orientation="h",
            template="plotly_dark",
            color="days_left",
            color_continuous_scale="teal"
        )

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(fig, use_container_width=True)

    with colB:
        risk_counts = df["risk_level"].value_counts()

        fig2 = go.Figure(
            data=[go.Pie(
                labels=risk_counts.index,
                values=risk_counts.values,
                hole=0.6
            )]
        )

        fig2.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(fig2, use_container_width=True)

    # ---------- AI DECISIONS ----------
    st.markdown("### 🤖 AI Agent Decisions")
    if not decisions_df.empty:
        st.dataframe(decisions_df, use_container_width=True, hide_index=True)
    else:
        st.info("No AI decisions available yet. Run the agent from Operations.")

# =====================================================
# ================= INVENTORY ==========================
# =====================================================
elif page == "Inventory":

    st.title("Asset Inventory")

    if df.empty:
        st.warning("No scan data available.")
        st.stop()

    search = st.text_input("Search Domain")

    display_df = df.copy()

    if search:
        display_df = display_df[
            display_df["domain"].str.contains(search, case=False)
        ]

    st.dataframe(display_df, use_container_width=True, hide_index=True)

# =====================================================
# REPLACE your existing "Operations" page block with this
# =====================================================
elif page == "Operations":

    st.title("Agentic Operations")
    st.write("Trigger the AI Agent to perform autonomous reasoning and tool execution.")

    if df.empty:
        st.warning("No scan data available.")
    else:
        for _, row in df.iterrows():

            c1, c2, c3 = st.columns([3, 1, 1])
            c1.markdown(f"**{row['domain']}**")

            days = int(row['days_left'])
            status_color = "red" if days <= 47 else "green"
            c2.markdown(f":{status_color}[{days} days remaining]")

            if c3.button("Run AI Agent", key=f"btn_{row['domain']}"):

                domain = row["domain"]

                with st.status(f"Agent is thinking about {domain}...", expanded=True) as status:

                    log_container = st.container()

                    # ── stream agent steps manually ──────────────────────
                    try:
                        from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
                        from langgraph.prebuilt import create_react_agent
                        from ai_agent import llm
                        from decision_agent import (
                            TOOLS, SYSTEM_PROMPT,
                            get_certificate_info,
                            renew_certificate,
                            verify_certificate,
                            save_decision,
                        )

                        agent = create_react_agent(
                            model=llm,
                            tools=TOOLS,
                            prompt=SYSTEM_PROMPT,
                        )

                        with log_container:
                            st.markdown("####  Agent trace")

                        # stream=True gives us each step as it happens
                        for chunk in agent.stream(
                            {"messages": [HumanMessage(content=f"Analyse TLS certificate health for: {domain}")]},
                        ):
                            # chunk keys: 'agent' or 'tools'
                            if "agent" in chunk:
                                for msg in chunk["agent"]["messages"]:
                                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                                        for tc in msg.tool_calls:
                                            with log_container:
                                                st.info(f"Calling tool: **{tc['name']}**  \nArgs: `{tc['args']}`")
                                    elif isinstance(msg, AIMessage) and msg.content:
                                        with log_container:
                                            st.success(f" Agent: {msg.content}")

                            if "tools" in chunk:
                                for msg in chunk["tools"]["messages"]:
                                    if isinstance(msg, ToolMessage):
                                        with log_container:
                                            st.markdown(
                                                f"<div style='background:#1a3a2a;padding:8px 12px;"
                                                f"border-radius:8px;border-left:3px solid #06b6d4;"
                                                f"font-size:13px;margin:4px 0'>"
                                                f" <b>{msg.name}</b>: {msg.content}</div>",
                                                unsafe_allow_html=True,
                                            )

                        status.update(label="Agent Task Finished", state="complete", expanded=False)

                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        status.update(label="Agent Error", state="error", expanded=False)