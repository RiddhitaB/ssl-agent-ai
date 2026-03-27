from .ai_agent import ai_evaluate_certificate
import json

def evaluate_risk(days_left: int, domain: str = None, issuer: str = None):
    try:
        ai_response = ai_evaluate_certificate(domain, issuer, days_left)
        parsed = json.loads(ai_response)
        return parsed["risk_level"]
    except Exception:
        # Fallback rule logic
        if days_left < 7:
            return "CRITICAL"
        elif days_left < 15:
            return "HIGH"
        elif days_left < 30:
            return "MEDIUM"
        elif days_left < 47:
            return "INFO"
        else:
            return "LOW"
