import subprocess

def renew_certificate(domain):
    """
    Simulates TLS certificate renewal using Certbot.
    Returns structured output for agent + dashboard.
    """

    print(f"\n Renewing certificate for {domain}...")

    try:
        result = subprocess.run(
            ["echo", f"Certbot renewal triggered for {domain}"],
            capture_output=True,
            text=True
        )

        output = result.stdout.strip()

        print(output)
        print(f" Renewal completed for {domain}")

        return {
            "domain": domain,
            "status": "SUCCESS",
            "message": output
        }

    except Exception as e:
        print(f"Renewal failed for {domain}")
        print(e)

        return {
            "domain": domain,
            "status": "FAILED",
            "message": str(e)
        }