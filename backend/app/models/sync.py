from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from datetime import datetime
from app.db.database import Base

class SyncEvent(Base):
    __tablename__ = "sync_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    client_id = Column(String, unique=True, index=True, nullable=False)
    
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    
    client_created_at = Column(DateTime, nullable=False)
    server_synced_at = Column(DateTime, default=datetime.utcnow)
