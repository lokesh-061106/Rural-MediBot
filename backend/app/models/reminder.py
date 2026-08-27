from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class Reminder(Base):
    __tablename__ = "reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    medicine_name = Column(String, nullable=False)
    dose = Column(String, nullable=True)
    time = Column(String, nullable=False) # e.g. "08:00"
    frequency = Column(String, nullable=False) # Daily, Weekly, etc.
    notes = Column(Text, nullable=True)
    
    active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", backref="reminders")
