import csv
import os
from datetime import datetime, timedelta
from langchain_core.tools import tool

SCAN_FILE = "tls_certificate_scan_history.csv"
DECISION_FILE = "tls_agent_decisions.csv"

# ─────────────────────────────────────────────
# CORE DETECTION LOGIC  (pure Python, no API)
# ─────────────────────────────────────────────

def _load_all_scans() -> dict[str, list[dict]]:
    """Load full scan history grouped by domain, sorted oldest→newest."""
    if not os.path.exists(SCAN_FILE):
        return {}

    history: dict[str, list[dict]] = {}
    with open(SCAN_FILE, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            domain = row["domain"]
            history.setdefault(domain, []).append(row)

    for domain in history:
        history[domain].sort(key=lambda r: r["timestamp"])

    return history


def _load_decisions() -> dict[str, dict]:
    """Load latest agent decision per domain."""
    if not os.path.exists(DECISION_FILE):
        return {}
    with open(DECISION_FILE, "r", encoding="utf-8") as f:
        return {row["domain"]: row for row in csv.DictReader(f)}


def _detect_for_domain(domain: str, scans: list[dict], decisions: dict) -> list[dict]:
    """Run all anomaly checks for one domain. Returns list of anomaly dicts."""
    anomalies = []
    now = datetime.utcnow()

    if not scans:
        return anomalies

    latest = scans[-1]
    latest_days = int(latest.get("days_left", 9999))
    latest_ts = datetime.strptime(latest["timestamp"], "%Y-%m-%d %H:%M:%S")

    # ── 1. RAPID DROP ──────────────────────────────────────────────────
    # days_left fell by more than 30 between any two consecutive scans
    for i in range(1, len(scans)):
        prev_days = int(scans[i - 1].get("days_left", 9999))
        curr_days = int(scans[i].get("days_left", 9999))
        drop = prev_days - curr_days

        # Normal expiry: ~1 day per day elapsed. A drop of 30+ in a short
        # period means early revocation or cert replacement gone wrong.
        prev_ts = datetime.strptime(scans[i - 1]["timestamp"], "%Y-%m-%d %H:%M:%S")
        curr_ts = datetime.strptime(scans[i]["timestamp"], "%Y-%m-%d %H:%M:%S")
        hours_elapsed = max((curr_ts - prev_ts).total_seconds() / 3600, 0.01)
        expected_drop = hours_elapsed / 24  # certs expire ~1 day per calendar day

        if drop > expected_drop + 30:
            anomalies.append({
                "type": "RAPID_DROP",
                "severity": "HIGH",
                "detail": (
                    f"days_left dropped by {drop} days between "
                    f"{scans[i-1]['timestamp']} and {scans[i]['timestamp']} "
                    f"(expected ~{expected_drop:.1f} days). "
                    f"Possible early revocation or cert swap failure."
                ),
            })

    # ── 2. STALE SCAN ──────────────────────────────────────────────────
    # No scan recorded in the last 7 days → scanner may be broken
    hours_since_scan = (now - latest_ts).total_seconds() / 3600
    if hours_since_scan > 7 * 24:
        anomalies.append({
            "type": "STALE_SCAN",
            "severity": "MEDIUM",
            "detail": (
                f"Last scan was {hours_since_scan/24:.1f} days ago "
                f"({latest['timestamp']}). Scanner may be offline or misconfigured."
            ),
        })

    # ── 3. MISSED RENEWAL ──────────────────────────────────────────────
    # Certificate is within 30 days of expiry but no RENEW decision exists
    if latest_days <= 30:
        decision = decisions.get(domain)
        if decision is None or "RENEW" not in decision.get("decision", "").upper():
            anomalies.append({
                "type": "MISSED_RENEWAL",
                "severity": "CRITICAL",
                "detail": (
                    f"Only {latest_days} days left but no renewal action is recorded "
                    f"in agent decisions. Certificate may expire without intervention."
                ),
            })

    # ── 4. OSCILLATING DAYS_LEFT ───────────────────────────────────────
    # days_left goes up then down across scans — indicates cert was replaced
    # but the new cert has a shorter validity than expected
    if len(scans) >= 3:
        days_series = [int(s.get("days_left", 0)) for s in scans[-5:]]
        increases = sum(1 for i in range(1, len(days_series)) if days_series[i] > days_series[i-1])
        if increases >= 2:
            anomalies.append({
                "type": "OSCILLATING_VALIDITY",
                "severity": "LOW",
                "detail": (
                    f"days_left has increased {increases} times across recent scans "
                    f"({days_series}). This may indicate repeated cert replacements "
                    f"or an unstable renewal process."
                ),
            })

    return anomalies


# ─────────────────────────────────────────────
# LANGCHAIN TOOL  (called by the AI agent)
# ─────────────────────────────────────────────

@tool
def detect_anomalies(domain: str) -> str:
    """
    Analyse the full scan history for a domain and detect anomalies.

    Detects:
    - RAPID_DROP: days_left fell sharply (possible early revocation)
    - STALE_SCAN: no scan in 7+ days (scanner may be offline)
    - MISSED_RENEWAL: expiring soon but no renewal recorded
    - OSCILLATING_VALIDITY: days_left bouncing up/down across scans

    Returns a plain-text anomaly report. Call this BEFORE deciding whether
    to renew — anomalies may change the urgency of your decision.
    """
    history = _load_all_scans()
    decisions = _load_decisions()

    if domain not in history:
        return f"No scan history found for {domain}. Cannot perform anomaly detection."

    scans = history[domain]
    anomalies = _detect_for_domain(domain, scans, decisions)

    if not anomalies:
        return (
            f"No anomalies detected for {domain}. "
            f"Scan history looks normal across {len(scans)} scans."
        )

    lines = [f"Anomalies detected for {domain} ({len(scans)} scans analysed):\n"]
    for i, a in enumerate(anomalies, 1):
        lines.append(
            f"{i}. [{a['severity']}] {a['type']}\n"
            f"   {a['detail']}"
        )

    return "\n".join(lines)


# ─────────────────────────────────────────────
# STANDALONE RUNNER  (test without agent)
# ─────────────────────────────────────────────

def run_anomaly_report():
    """Print anomaly report for all domains. Run directly to test."""
    history = _load_all_scans()
    decisions = _load_decisions()

    if not history:
        print("No scan history found.")
        return

    print("=" * 60)
    print("  TLS ANOMALY DETECTION REPORT")
    print(f"  Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)

    total_anomalies = 0
    for domain, scans in sorted(history.items()):
        anomalies = _detect_for_domain(domain, scans, decisions)
        total_anomalies += len(anomalies)

        if anomalies:
            print(f"\n  {domain}  ({len(scans)} scans)")
            for a in anomalies:
                print(f"    [{a['severity']}] {a['type']}")
                print(f"    {a['detail']}")
        else:
            print(f"\n  {domain}  — no anomalies")

    print(f"\n{'='*60}")
    print(f"  Total anomalies found: {total_anomalies}")
    print("=" * 60)


if __name__ == "__main__":
    run_anomaly_report()