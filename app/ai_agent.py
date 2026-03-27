from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def ai_evaluate_certificate(domain: str, issuer: str, days_left: int):
    prompt = f"""
    You are a cybersecurity AI agent.

    Evaluate the TLS certificate risk based on:
    - Domain: {domain}
    - Issuer: {issuer}
    - Days until expiry: {days_left}

    Return ONLY valid JSON in this format:
    {{
        "risk_level": "...",
        "reason": "..."
    }}

    Risk levels allowed:
    LOW, INFO, MEDIUM, HIGH, CRITICAL
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return response.choices[0].message.content
