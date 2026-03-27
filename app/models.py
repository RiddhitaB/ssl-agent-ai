from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func  # ✅ Move to top
from .database import Base

class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, index=True, nullable=False)
    issuer = Column(String)
    days_left = Column(Integer)
    risk_level = Column(String)
    last_checked = Column(DateTime, server_default=func.now())
