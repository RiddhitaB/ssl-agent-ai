from pydantic import BaseModel

class CertificateCreate(BaseModel):
    domain: str
    issuer: str
    days_left: int
