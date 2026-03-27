from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from .database import engine, SessionLocal
from . import models
from . import schemas
from .agent_controller import evaluate_risk



models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "TLS Agent Backend Connected to PostgreSQL"}

@app.post("/certificates/")
def create_certificate(
    cert_data: schemas.CertificateCreate,
    db: Session = Depends(get_db)
):
    risk = evaluate_risk(
        cert_data.days_left,
        cert_data.domain,
        cert_data.issuer
    )

    cert = models.Certificate(
        domain=cert_data.domain,
        issuer=cert_data.issuer,
        days_left=cert_data.days_left,
        risk_level=risk
    )

    db.add(cert)
    db.commit()
    db.refresh(cert)

    return cert


@app.get("/certificates/")
def get_certificates(db: Session = Depends(get_db)):
    return db.query(models.Certificate).all()

@app.post("/agent/evaluate")
def agent_evaluate(cert_data: schemas.CertificateCreate):
    risk = evaluate_risk(cert_data.days_left)

    return {
        "domain": cert_data.domain,
        "evaluated_risk": risk,
        "message": f"Certificate evaluated as {risk} risk."
    }
