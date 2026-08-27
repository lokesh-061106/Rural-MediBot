from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class Consultation(Base):
    __tablename__ = "consultations"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True) # can be null if unassigned
    
    status = Column(String, default="PENDING", index=True) # PENDING, ACCEPTED, COMPLETED, CANCELLED
    risk_level = Column(String, default="Low") # Low, Moderate, High
    
    symptoms = Column(Text, nullable=False)
    ai_assessment = Column(Text, nullable=True)
    doctor_notes = Column(Text, nullable=True)
    
    scheduled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    patient = relationship("User", foreign_keys=[patient_id], backref="patient_consultations")
    doctor = relationship("User", foreign_keys=[doctor_id], backref="doctor_consultations")
