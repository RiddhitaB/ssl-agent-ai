import ssl
import socket
from datetime import datetime

RENEWAL_THRESHOLD_DAYS = 47


def scan_certificate(domain, port=443):
    context = ssl.create_default_context()

    with socket.create_connection((domain, port)) as sock:
        with context.wrap_socket(sock, server_hostname=domain) as ssock:
            cert = ssock.getpeercert()
            tls_version = ssock.version()

    # Parse certificate dates
    not_after = cert['notAfter']
    not_before = cert['notBefore']

    expiry_date = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
    issue_date = datetime.strptime(not_before, "%b %d %H:%M:%S %Y %Z")

    days_left = (expiry_date - datetime.utcnow()).days

    issuer = dict(x[0] for x in cert['issuer'])
    issuer_name = issuer.get("organizationName", "Unknown")

    risk_level = classify_risk(days_left)
    renewal_required = days_left <= RENEWAL_THRESHOLD_DAYS

    return {
        "domain": domain,
        "issuer": issuer_name,
        "issued_on": issue_date,
        "expires_on": expiry_date,
        "days_left": days_left,
        "tls_version": tls_version,
        "risk_level": risk_level,
        "renewal_required": renewal_required
    }


def classify_risk(days_left):
    if days_left <= 0:
        return "EXPIRED"
    elif days_left <= 47:
        return "CRITICAL"
    elif days_left <= 90:
        return "WARNING"
    else:
        return "SAFE"


if __name__ == "__main__":
    domain = "google.com"   # change this to any real website
    result = scan_certificate(domain)

    print("\n🔐 TLS / SSL Certificate Scan Result")
    print("===================================")
    print(f"Domain            : {result['domain']}")
    print(f"Issuer            : {result['issuer']}")
    print(f"TLS Version       : {result['tls_version']}")
    print(f"Issued On         : {result['issued_on']}")
    print(f"Expires On        : {result['expires_on']}")
    print(f"Days Remaining    : {result['days_left']}")
    print(f"Risk Level        : {result['risk_level']}")

    if result["renewal_required"]:
        print("⚠️ Renewal Status  : REQUIRED (≤ 47 days)")
    else:
        print("✅ Renewal Status : NOT REQUIRED")
