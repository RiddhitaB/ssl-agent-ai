# tools.py
from langchain_core.tools import tool
import subprocess
import ssl
import socket
import csv
import os
from datetime import datetime
import pandas as pd

SCAN_FILE = "tls_certificate_scan_history.csv"
DECISION_FILE = "tls_agent_decisions.csv"


# =========================================================
# TOOL 1: RENEW CERTIFICATE
# =========================================================
@tool
def renew_certificate(domain: str) -> str:
    """Simulate certificate renewal using Certbot."""
    try:
        result = subprocess.run(
            ["echo", f"Certbot renewal triggered for {domain}"],
            capture_output=True, text=True, timeout=10
        )
        return f"SUCCESS: Certificate renewal triggered for {domain}\nLog: {result.stdout.strip()}"
    except Exception as e:
        return f"FAILED: Renewal failed for {domain} → {str(e)}"


# =========================================================
# TOOL 2: VERIFY CERTIFICATE
# =========================================================
@tool
def verify_certificate(domain: str) -> str:
    """Fetch live SSL certificate and calculate remaining days."""
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=8) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()

        expire_date = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
        days_left = (expire_date - datetime.utcnow()).days

        return (
            f"VERIFIED: {domain}\n"
            f"Expiry Date: {expire_date.date()}\n"
            f"Days Remaining: {days_left}"
        )
    except socket.timeout:
        return f"ERROR: Timeout connecting to {domain} (port 443)"
    except ssl.SSLError:
        return f"ERROR: SSL handshake failed for {domain}"
    except Exception as e:
        return f"ERROR: Could not verify {domain} → {str(e)}"


# =========================================================
# TOOL 3: RENEW + VERIFY COMBO
# =========================================================
@tool
def renew_and_verify(domain: str) -> str:
    """Combined renewal and verification."""
    renewal = renew_certificate.invoke(domain)
    verification = verify_certificate.invoke(domain)
    return f"{renewal}\n\n{verification}"


# =========================================================
# TOOL 4: DETECT ANOMALIES (FIXED & ROBUST)
# =========================================================
def _load_all_scans() -> dict:
    """Load scan history grouped by domain."""
    if not os.path.exists(SCAN_FILE):
        return {}
    try:
        df = pd.read_csv(SCAN_FILE)
        history = {}
        for domain, group in df.groupby("domain"):
            history[domain] = group.sort_values("timestamp").to_dict("records")
        return history
    except Exception as e:
        print(f"Warning: Could not load scan history: {e}")
        return {}


def _load_decisions() -> dict:
    """Load latest decisions per domain."""
    if not os.path.exists(DECISION_FILE):
        return {}
    try:
        df = pd.read_csv(DECISION_FILE)
        return df.groupby("domain").last().to_dict("index")
    except Exception:
        return {}


@tool
def detect_anomalies(domain: str) -> str:
    """
    Detect anomalies in certificate scan history.
    Returns clear, concise report for agents.
    """
    try:
        history = _load_all_scans()
        decisions = _load_decisions()

        if domain not in history or not history[domain]:
            return f"No scan history found for {domain}. Anomaly detection skipped."

        scans = history[domain]
        now = datetime.utcnow()
        anomalies = []

        latest = scans[-1]
        latest_days = int(latest.get("days_left", 9999))
        try:
            latest_ts = datetime.strptime(latest["timestamp"], "%Y-%m-%d %H:%M:%S")
        except:
            latest_ts = now

        # 1. RAPID DROP
        for i in range(1, len(scans)):
            try:
                prev_days = int(scans[i-1].get("days_left", 9999))
                curr_days = int(scans[i].get("days_left", 9999))
                drop = prev_days - curr_days
                prev_ts = datetime.strptime(scans[i-1]["timestamp"], "%Y-%m-%d %H:%M:%S")
                curr_ts = datetime.strptime(scans[i]["timestamp"], "%Y-%m-%d %H:%M:%S")
                hours_elapsed = max((curr_ts - prev_ts).total_seconds() / 3600, 0.01)
                expected_drop = hours_elapsed / 24

                if drop > expected_drop + 30:
                    anomalies.append(f"RAPID_DROP (HIGH): Days left dropped by {drop} (expected ~{expected_drop:.1f})")
            except:
                continue

        # 2. STALE SCAN
        hours_since = (now - latest_ts).total_seconds() / 3600
        if hours_since > 7 * 24:
            anomalies.append(f"STALE_SCAN (MEDIUM): Last scan was {hours_since/24:.1f} days ago.")

        # 3. MISSED RENEWAL
        if latest_days <= 30:
            decision = decisions.get(domain)
            if not decision or "RENEW" not in str(decision.get("decision", "")).upper():
                anomalies.append(f"MISSED_RENEWAL (CRITICAL): Only {latest_days} days left but no renewal recorded.")

        # 4. OSCILLATING
        if len(scans) >= 3:
            try:
                series = [int(s.get("days_left", 0)) for s in scans[-5:]]
                increases = sum(1 for i in range(1, len(series)) if series[i] > series[i-1])
                if increases >= 2:
                    anomalies.append(f"OSCILLATING (LOW): days_left increased {increases} times in recent scans.")
            except:
                pass

        if not anomalies:
            return f"No anomalies detected for {domain} ({len(scans)} scans analysed). History looks stable."

        report = f" Anomalies detected for {domain} ({len(scans)} scans):\n"
        for i, anomaly in enumerate(anomalies, 1):
            report += f"{i}. {anomaly}\n"
        return report

    except Exception as e:
        return f"ERROR in anomaly detection for {domain}: {str(e)}"