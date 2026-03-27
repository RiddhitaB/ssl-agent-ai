import ssl
import socket
import csv
from datetime import datetime

RENEWAL_THRESHOLD_DAYS = 47


def classify_risk(days_left):
    if days_left <= 0:
        return "EXPIRED"
    elif days_left <= RENEWAL_THRESHOLD_DAYS:
        return "CRITICAL"
    elif days_left <= 90:
        return "WARNING"
    else:
        return "SAFE"


def scan_certificate(domain, port=443):
    context = ssl.create_default_context()

    with socket.create_connection((domain, port), timeout=6) as sock:
        with context.wrap_socket(sock, server_hostname=domain) as ssock:
            cert = ssock.getpeercert()
            tls_version = ssock.version()

    expiry_date = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
    days_left = (expiry_date - datetime.utcnow()).days

    issuer = dict(x[0] for x in cert['issuer'])
    issuer_name = issuer.get("organizationName", "Unknown")

    return [
        domain,
        issuer_name,
        tls_version,
        expiry_date.strftime("%Y-%m-%d"),
        days_left,
        classify_risk(days_left),
        "YES" if days_left <= RENEWAL_THRESHOLD_DAYS else "NO"
    ]


websites = [
    # Tech
    "google.com","github.com","cloudflare.com","openai.com","microsoft.com","apple.com",
    # Knowledge
    "wikipedia.org","ieee.org","springer.com","sciencedirect.com",
    # Finance
    "paypal.com","visa.com","mastercard.com","hdfcbank.com","sbi.co.in",
    # Govt
    "india.gov.in","gov.uk","usa.gov","who.int","un.org",
    # E-commerce
    "amazon.com","flipkart.com","shopify.com","ebay.com",
    # Cloud
    "aws.amazon.com","azure.microsoft.com","digitalocean.com","vercel.com","netlify.com"
]

with open("tls_certificate_dataset.csv", "w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow([
        "Domain",
        "Issuer",
        "TLS_Version",
        "Expiry_Date",
        "Days_Left",
        "Risk_Level",
        "Renewal_Required"
    ])

    for site in websites:
        try:
            row = scan_certificate(site)
            writer.writerow(row)
            print(f"✔ Scanned {site}")
        except Exception as e:
            print(f"Failed {site}: {e}")

print("\nCSV file created: tls_certificate_dataset.csv")
