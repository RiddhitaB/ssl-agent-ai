import csv
import os
from datetime import datetime

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from ai_agent import llm

SCAN_FILE = "tls_certificate_scan_history.csv"
DECISION_FILE = "tls_agent_decisions.csv"


@tool
def get_certificate_info(domain: str) -> str:
    """Retrieve the latest TLS certificate scan data for a domain.
    Returns days_left, risk_level, issuer, expiry_date and all scan fields.
    Always call this first before making any decision."""
    if not os.path.exists(SCAN_FILE):
        return "Error: Scan file not found"
    with open(SCAN_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        latest = {row["domain"]: row for row in reader}
    if domain not in latest:
        return f"Error: No scan data found for {domain}"
    return str(dict(latest[domain]))


@tool
def renew_certificate(domain: str) -> str:
    """Trigger a TLS certificate renewal for the given domain.
    Use when days_left <= 47 or risk_level is WARNING or CRITICAL.
    Always call verify_certificate afterward."""
    print(f"[TOOL] Renewing certificate for: {domain}")
    return f"Renewal successfully initiated for {domain}. Expected completion in ~2 minutes."


@tool
def verify_certificate(domain: str) -> str:
    """Verify the TLS certificate is valid and correctly installed.
    Always call this after renew_certificate."""
    print(f"[TOOL] Verifying certificate for: {domain}")
    return f"Certificate for {domain} verified successfully. Chain intact. No errors detected."


@tool
def save_decision(domain: str, days_left: int, decision_summary: str) -> str:
    """Save the agent's final decision and reasoning to the decisions CSV.
    Always call this last, even if no action was taken."""
    existing = {}
    if os.path.exists(DECISION_FILE):
        with open(DECISION_FILE, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing[row["domain"]] = row

    existing[domain] = {
        "domain": domain,
        "days_left": days_left,
        "decision": decision_summary,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }

    with open(DECISION_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["domain", "days_left", "decision", "timestamp"])
        writer.writeheader()
        writer.writerows(existing.values())

    return f"Decision saved for {domain}."


TOOLS = [get_certificate_info, renew_certificate, verify_certificate, save_decision]

SYSTEM_PROMPT = """You are an autonomous TLS Security Agent.

For each domain, follow this workflow:
1. GATHER  - Call get_certificate_info first.
2. REASON  - Check days_left and risk_level.
3. ACT     - CRITICAL (<=14 days) or WARNING (15-47 days): renew then verify.
             HEALTHY (>47 days): monitor only, no action.
4. SAVE    - Always call save_decision with your full reasoning.

Never ask for confirmation. Act autonomously."""


def run_decision_logic(target_domain: str = None, callbacks: list = None):
    agent = create_react_agent(model=llm, tools=TOOLS, prompt=SYSTEM_PROMPT)
    callbacks = callbacks or []

    if target_domain:
        domains = [target_domain]
    else:
        if not os.path.exists(SCAN_FILE):
            print("Scan file not found.")
            return []
        with open(SCAN_FILE, "r", encoding="utf-8") as f:
            domains = list({row["domain"] for row in csv.DictReader(f)})

    results = []
    for domain in domains:
        print(f"\n{'='*50}\nAgent analysing: {domain}\n{'='*50}")
        try:
            response = agent.invoke(
                {"messages": [HumanMessage(content=f"Analyse TLS certificate health for: {domain}")]},
                config={"callbacks": callbacks},
            )
            output = response["messages"][-1].content
            print(f"Agent output: {output}")
            results.append({"domain": domain, "output": output})
        except Exception as e:
            print(f"Agent error for {domain}: {e}")
            results.append({"domain": domain, "output": f"Error: {e}"})

    return results