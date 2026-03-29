import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# Import multi-agent system
from multi_agent_system import run_multi_agent_system

st.set_page_config(layout="wide", page_title="TLS Monitor")

# ---------- CUSTOM CSS ----------
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
}
.stDataFrame {
    background-color: #26247a;
    border-radius: 18px;
}
.stButton>button {
    background: linear-gradient(90deg, #06b6d4, #3b82f6);
    border-radius: 14px;
    padding: 0.6rem 1.2rem;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ---------- LOAD DATA ----------
def load_data():
    try:
        df = pd.read_csv("tls_certificate_scan_history.csv")
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        latest = df.sort_values("timestamp").groupby("domain").tail(1)
        return latest
    except:
        return pd.DataFrame()

def load_agent_decisions():
    try:
        return pd.read_csv("tls_agent_decisions.csv")
    except:
        return pd.DataFrame()

df = load_data()
decisions_df = load_agent_decisions()

st_autorefresh(interval=60000, key="refresh")

# ---------- SIDEBAR ----------
with st.sidebar:
    st.title("🔐 TLS Monitor")
    page = st.radio("Navigation", ["Dashboard", "Inventory", "Operations", "🤖 Multi-Agent AI"])
    st.caption(f"Last refresh: {datetime.utcnow().strftime('%H:%M:%S UTC')}")

# =====================================================
# ================= DASHBOARD ==========================
# =====================================================
if page == "Dashboard":
    st.title("Infrastructure Analytics")

    if df.empty:
        st.warning("No scan data available. Run scanner first.")
        st.stop()

    total = len(df)
    critical = len(df[df.get("risk_level", pd.Series()) == "CRITICAL"])
    avg_days = int(df["days_left"].mean()) if not df.empty else 0
    compliance = round(((total - critical) / total) * 100, 1) if total > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Managed Assets", total)
    c2.metric("Critical Certificates", critical)
    c3.metric("Average Days Remaining", avg_days)
    c4.metric("Compliance %", f"{compliance}%")

    colA, colB = st.columns([2, 1])
    with colA:
        fig = px.bar(
            df.sort_values("days_left").head(10),
            x="days_left", y="domain",
            orientation="h",
            template="plotly_dark",
            color="days_left",
            color_continuous_scale="teal"
        )
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    with colB:
        risk_counts = df.get("risk_level", pd.Series()).value_counts()
        fig2 = go.Figure(data=[go.Pie(labels=risk_counts.index, values=risk_counts.values, hole=0.6)])
        fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### AI Agent Decisions")
    if not decisions_df.empty:
        st.dataframe(decisions_df, use_container_width=True, hide_index=True)
    else:
        st.info("No AI decisions yet. Run agents from Operations or Multi-Agent AI.")

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
        display_df = display_df[display_df["domain"].str.contains(search, case=False)]

    st.dataframe(display_df, use_container_width=True, hide_index=True)

# =====================================================
# ================= OPERATIONS =========================
# =====================================================
elif page == "Operations":
    st.title("Agentic Operations")
    st.write("Trigger individual AI agent for autonomous certificate management.")

    if df.empty:
        st.warning("No scan data available.")
    else:
        for _, row in df.iterrows():
            domain = row["domain"]
            days = int(row.get("days_left", 999))

            c1, c2, c3 = st.columns([3, 1, 1])
            c1.markdown(f"**{domain}**")
            status_color = "red" if days <= 47 else "green"
            c2.markdown(f":{status_color}[{days} days remaining]")
            
            if c3.button("Run Single Agent", key=f"btn_{domain}"):
                with st.status(f"Analyzing {domain}...", expanded=True) as status:
                    try:
                        from decision_agent import run_decision_logic
                        results = run_decision_logic(domain)
                        st.success(f"Completed for {domain}")
                        if results:
                            for r in results:
                                st.info(r.get('output', str(r)))
                        status.update(label="Task Finished", state="complete")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        st.exception(e)

# =====================================================
# ================= MULTI-AGENT AI =====================
# =====================================================
elif page == "🤖 Multi-Agent AI":
    st.title("🤖 Fully Agentic Multi-Agent AI System")
    st.markdown("**Collaborative team of 4 agents** working together on TLS certificate management.")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        quick_mode = st.checkbox("⚡ Quick Mode (much faster)", value=True)
    with col2:
        max_domains = st.number_input("Max domains to process", min_value=1, max_value=30, value=5, step=1)
    with col3:
        run_button = st.button("🚀 Run Multi-Agent System", type="primary", use_container_width=True)

    if run_button:
        # Create containers safely BEFORE running heavy code
        status_container = st.status("🤖 Multi-Agent Team is collaborating...", expanded=True)
        live_log_area = status_container.empty()
        final_results_container = st.container()

        def live_log(message: str):
            """Safe live logging"""
            live_log_area.markdown(f"{message.replace('\n', '  \n')}")
            print(message)  # also visible in terminal

        try:
            # Load domains
            if os.path.exists("tls_certificate_scan_history.csv"):
                df_load = pd.read_csv("tls_certificate_scan_history.csv")
                all_domains = df_load["domain"].unique().tolist()[:max_domains]
            else:
                all_domains = ["apple.com", "google.com", "paypal.com"]

            live_log(f"🚀 Starting on **{len(all_domains)}** domains in {'Quick' if quick_mode else 'Full'} mode...")

            # Run the multi-agent system
            results = run_multi_agent_system(
                selected_domains=all_domains,
                quick_mode=quick_mode,
                progress_callback=live_log
            )

            # Update status
            status_container.update(
                label=f"✅ Multi-Agent System Completed! Processed {len(results)} domains.",
                state="complete"
            )

            # Summary Table
            final_results_container.success("**Results Summary**")
            results_df = pd.DataFrame(results)
            display_cols = ["domain", "final_status", "decision"]
            if not quick_mode and "execution" in results_df.columns:
                display_cols.append("execution")

            final_results_container.dataframe(
                results_df[display_cols],
                use_container_width=True,
                hide_index=True
            )

            # Detailed Expanders
            st.subheader("📋 Full Agent Details")
            for i, res in enumerate(results):
                with st.expander(f"🔍 {res['domain']} — {res.get('final_status', 'Done')}", expanded=False):
                    st.markdown("**Anomaly Agent**")
                    st.text_area("Anomaly Report", res.get("anomaly_report", ""), height=130, key=f"ano_{i}")
                    
                    st.markdown("**Assessment Agent**")
                    st.text_area("Assessment", res.get("assessment", ""), height=110, key=f"ass_{i}")
                    
                    st.markdown("**Decision Agent**")
                    st.text_area("Decision", res.get("decision", ""), height=110, key=f"dec_{i}")
                    
                    st.markdown("**Execution Agent**")
                    st.text_area("Execution", res.get("execution", ""), height=110, key=f"exe_{i}")

        except Exception as e:
            status_container.update(label="❌ Error occurred", state="error")
            st.error(f"System Error: {str(e)}")
            st.exception(e)