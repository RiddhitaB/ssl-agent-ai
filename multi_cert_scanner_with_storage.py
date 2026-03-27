import streamlit as st
import pandas as pd
import subprocess
import plotly.express as px
import plotly.graph_objects as go
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ---------------- CONFIGURATION ----------------
st.set_page_config(
    page_title="TLS INFRASTRUCTURE MONITOR",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- PROFESSIONAL DARK THEME ----------------
st.markdown("""
<style>
.stApp {
    background-color: #0b0e14;
    color: #e2e8f0;
}
div[data-testid="stMetric"] {
    background-color: #161b22;
    border: 1px solid #30363d;
    padding: 1.5rem;
    border-radius: 4px;
}
section[data-testid="stSidebar"] {
    background-color: #0d1117;
    border-right: 1px solid #30363d;
}
h1, h2, h3 {
    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    letter-spacing: -0.01em;
    color: #f0f6fc;
}
.stDataFrame {
    border: 1px solid #30363d;
}
.stButton>button {
    border-radius: 2px;
    text-transform: uppercase;
    font-size: 12px;
    letter-spacing: 1px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ---------------- DATA LOADER ----------------
def load_and_process_data():
    try:
        df = pd.read_csv("tls_certificate_scan_history.csv")
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        latest = df.sort_values("timestamp").groupby("domain").tail(1)
        return latest
    except Exception:
        return pd.DataFrame()

df_latest = load_and_process_data()

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.markdown("### TLS GOVERNANCE")
    st.markdown("---")
    page = st.radio("NAVIGATION", 
                    ["NETWORK DASHBOARD", 
                     "ASSET INVENTORY", 
                     "AGENT OPERATIONS"])
    
    st.markdown("---")
    st.caption("SYSTEM STATUS: NOMINAL")
    st.caption(f"REFRESH UTC: {datetime.utcnow().strftime('%H:%M:%S')}")

# ---------------- AUTO REFRESH ----------------
st_autorefresh(interval=60000, limit=1000, key="system_heartbeat")

# ==========================================================
# =================== NETWORK DASHBOARD ====================
# ==========================================================
if page == "NETWORK DASHBOARD":

    st.markdown("## TLS COMPLIANCE OVERVIEW")

    if df_latest.empty:
        st.info("No active scan data found in the history repository.")
        st.stop()

    # ----- METRICS -----
    m1, m2, m3, m4 = st.columns(4)

    total_assets = len(df_latest)
    critical_risk = len(df_latest[df_latest["risk_level"] == "CRITICAL"])
    avg_expiry = int(df_latest["days_left"].mean())

    if total_assets > 0:
        compliance_pct = round(((total_assets - critical_risk) / total_assets) * 100, 1)
    else:
        compliance_pct = 0

    m1.metric("TOTAL MANAGED ASSETS", total_assets)
    m2.metric("CRITICAL VULNERABILITIES", critical_risk, delta_color="inverse")
    m3.metric("AVG DAYS TO EXPIRY", avg_expiry)
    m4.metric("INFRASTRUCTURE HEALTH", f"{compliance_pct}%")

    st.markdown("---")

    # ----- ANALYTICS -----
    col_a, col_b = st.columns([3, 2])

    # EXPIRATION FORECAST
    with col_a:
        st.markdown("### EXPIRATION FORECAST")

        fig = px.bar(
            df_latest.sort_values("days_left", ascending=True).head(15),
            x="days_left",
            y="domain",
            orientation='h',
            color="days_left",
            color_continuous_scale="Blues",
            template="plotly_dark"
        )

        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title="DAYS REMAINING",
            yaxis_title=None
        )

        st.plotly_chart(fig, use_container_width=True)

    # RISK CLASSIFICATION
    with col_b:
        st.markdown("### RISK CLASSIFICATION")

        risk_counts = df_latest["risk_level"].value_counts()

        risk_map = {
            'CRITICAL': '#ff4b4b',
            'HIGH': '#ffa500',
            'MEDIUM': '#1f77b4',
            'LOW': '#00cc96'
        }

        fig2 = go.Figure(data=[go.Pie(
            labels=risk_counts.index,
            values=risk_counts.values,
            hole=.6,
            marker=dict(colors=[risk_map.get(x, '#333') for x in risk_counts.index])
        )])

        fig2.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True
        )

        st.plotly_chart(fig2, use_container_width=True)

    # ----- CRITICAL LIST -----
    st.markdown("### CRITICAL ACTION REQUIRED")

    critical_df = df_latest[df_latest["risk_level"] == "CRITICAL"][
        ["domain", "days_left", "risk_level"]
    ]

    st.dataframe(critical_df, use_container_width=True, hide_index=True)

# ==========================================================
# ==================== ASSET INVENTORY =====================
# ==========================================================
elif page == "ASSET INVENTORY":

    st.markdown("## GLOBAL ASSET REPOSITORY")

    if df_latest.empty:
        st.info("No asset data available.")
        st.stop()

    search_query = st.text_input("FILTER BY DOMAIN NAME", "")

    display_df = df_latest.copy()

    if search_query:
        display_df = display_df[
            display_df["domain"].str.contains(search_query, case=False)
        ]

    st.dataframe(
        display_df.sort_values("days_left"),
        use_container_width=True,
        hide_index=True
    )

# ==========================================================
# ==================== AGENT OPERATIONS ====================
# ==========================================================
elif page == "AGENT OPERATIONS":

    st.markdown("## AUTOMATED RENEWAL CONTROL")

    st.markdown("""
    The AI Renewal Agent operates on high-risk assets.  
    It performs validation, CSR generation, and deployment simulation.
    """)

    if st.button("INITIATE AGENT SEQUENCE", use_container_width=True):

        with st.status("EXECUTING PROTOCOL", expanded=True) as status:

            st.write("Checking system dependencies...")
            time.sleep(1)

            st.write("Analyzing risk vectors...")

            try:
                result = subprocess.run(
                    ["python", "agent_controller.py"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode == 0:
                    st.write("Deployment sequence verified.")
                    status.update(label="SEQUENCE COMPLETE", state="complete")

                    if result.stdout:
                        st.code(result.stdout)

                else:
                    st.error("Protocol failure.")
                    if result.stderr:
                        st.code(result.stderr)

            except Exception as e:
                st.error(f"Operational error: {str(e)}")

# ---------------- FOOTER ----------------
st.markdown("---")
st.caption("INTERNAL USE ONLY | ENCRYPTED TRANSPORT MONITORING")
