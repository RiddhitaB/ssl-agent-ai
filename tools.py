from langchain_core.tools import tool   # use langchain_core, not langchain.tools
import subprocess
import ssl
import socket
import csv
import os
from datetime import datetime

SCAN_FILE = "tls_certificate_scan_history.csv"
DECISION_FILE = "tls_agent_decisions.csv"


# =========================================================
# TOOL 1: RENEW CERTIFICATE
# =========================================================
@tool
def renew_certificate(domain: str) -> str:
    """
    Renew TLS certificate using Certbot.
    This simulates renewal (safe for local/demo use).
    """
    try:
        result = subprocess.run(
            ["echo", f"Certbot renewal triggered for {domain}"],
            capture_output=True,
            text=True
        )
        return (
            f"SUCCESS: Certificate renewal triggered for {domain}\n"
            f"Log: {result.stdout.strip()}"
        )
    except Exception as e:
        return f"FAILED: Renewal failed for {domain} → {str(e)}"


# =========================================================
# TOOL 2: VERIFY CERTIFICATE
# =========================================================
@tool
def verify_certificate(domain: str) -> str:
    """
    Verify TLS certificate expiry for a domain.
    Fetches live SSL certificate and calculates remaining days.
    """
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()

        expire_date = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
        days_left = (expire_date - datetime.utcnow()).days

        return (
            f"VERIFIED: {domain}\n"
            f"Expiry Date: {expire_date}\n"
            f"Days Remaining: {days_left}"
        )
    except Exception as e:
        return f"ERROR: Could not verify {domain} → {str(e)}"


# =========================================================
# TOOL 3: RENEW + VERIFY COMBO
# =========================================================
@tool
def renew_and_verify(domain: str) -> str:
    """
    Perform renewal and immediately verify the certificate.
    Useful for agent chaining or fallback execution.
    """
    renewal_result = renew_certificate.invoke(domain)
    verification_result = verify_certificate.invoke(domain)
    return f"{renewal_result}\n\n{verification_result}"


# =========================================================
# TOOL 4: DETECT ANOMALIES  ← NEW
# =========================================================

def _load_all_scans() -> dict:
    """Load full scan history grouped by domain, sorted oldest→newest."""
    if not os.path.exists(SCAN_FILE):
        return {}
    history = {}
    with open(SCAN_FILE, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            history.setdefault(row["domain"], []).append(row)
    for domain in history:
        history[domain].sort(key=lambda r: r["timestamp"])
    return history


def _load_decisions() -> dict:
    """Load latest agent decision per domain."""
    if not os.path.exists(DECISION_FILE):
        return {}
    with open(DECISION_FILE, "r", encoding="utf-8") as f:
        return {row["domain"]: row for row in csv.DictReader(f)}


@tool
def detect_anomalies(domain: str) -> str:
    """
    Analyse the full scan history for a domain and detect anomalies.

    Detects:
    - RAPID_DROP    : days_left fell sharply between scans (possible early revocation)
    - STALE_SCAN    : no scan recorded in 7+ days (scanner may be offline)
    - MISSED_RENEWAL: certificate expiring soon but no renewal action recorded
    - OSCILLATING   : days_left bouncing up and down (unstable renewal process)

    Always call this BEFORE deciding whether to renew — anomalies can raise
    urgency even when days_left looks safe on its own.
    """
    history = _load_all_scans()
    decisions = _load_decisions()

    if domain not in history:
        return f"No scan history found for {domain}. Cannot perform anomaly detection."

    scans = history[domain]
    now = datetime.utcnow()
    anomalies = []

    latest = scans[-1]
    latest_days = int(latest.get("days_left", 9999))
    latest_ts = datetime.strptime(latest["timestamp"], "%Y-%m-%d %H:%M:%S")

    # 1. RAPID DROP
    for i in range(1, len(scans)):
        prev_days = int(scans[i - 1].get("days_left", 9999))
        curr_days = int(scans[i].get("days_left", 9999))
        drop = prev_days - curr_days
        prev_ts = datetime.strptime(scans[i - 1]["timestamp"], "%Y-%m-%d %H:%M:%S")
        curr_ts = datetime.strptime(scans[i]["timestamp"], "%Y-%m-%d %H:%M:%S")
        hours_elapsed = max((curr_ts - prev_ts).total_seconds() / 3600, 0.01)
        expected_drop = hours_elapsed / 24
        if drop > expected_drop + 30:
            anomalies.append({
                "type": "RAPID_DROP", "severity": "HIGH",
                "detail": (
                    f"days_left dropped by {drop} days between "
                    f"{scans[i-1]['timestamp']} and {scans[i]['timestamp']} "
                    f"(expected ~{expected_drop:.1f}). Possible early revocation."
                )
            })

    # 2. STALE SCAN
    hours_since = (now - latest_ts).total_seconds() / 3600
    if hours_since > 7 * 24:
        anomalies.append({
            "type": "STALE_SCAN", "severity": "MEDIUM",
            "detail": (
                f"Last scan was {hours_since/24:.1f} days ago ({latest['timestamp']}). "
                f"Scanner may be offline or misconfigured."
            )
        })

    # 3. MISSED RENEWAL
    if latest_days <= 30:
        decision = decisions.get(domain)
        if decision is None or "RENEW" not in decision.get("decision", "").upper():
            anomalies.append({
                "type": "MISSED_RENEWAL", "severity": "CRITICAL",
                "detail": (
                    f"Only {latest_days} days left but no renewal is recorded. "
                    f"Certificate may expire without intervention."
                )
            })

    # 4. OSCILLATING VALIDITY
    if len(scans) >= 3:
        series = [int(s.get("days_left", 0)) for s in scans[-5:]]
        increases = sum(1 for i in range(1, len(series)) if series[i] > series[i - 1])
        if increases >= 2:
            anomalies.append({
                "type": "OSCILLATING", "severity": "LOW",
                "detail": (
                    f"days_left increased {increases} times across recent scans "
                    f"{series}. Possible unstable renewal process."
                )
            })

    if not anomalies:
        return (
            f"No anomalies detected for {domain}. "
            f"History looks normal across {len(scans)} scan(s)."
        )

    lines = [f"Anomalies detected for {domain} ({len(scans)} scan(s) analysed):\n"]
    for i, a in enumerate(anomalies, 1):
        lines.append(f"{i}. [{a['severity']}] {a['type']}\n   {a['detail']}")
    return "\n".join(lines)