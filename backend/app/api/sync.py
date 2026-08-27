from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime

router = APIRouter()

class SyncEventBase(BaseModel):
    client_id: str
    event_type: str
    payload: Dict[str, Any]
    created_at: str

class SyncBatchRequest(BaseModel):
    events: List[SyncEventBase]

class SyncResponse(BaseModel):
    synced_client_ids: List[str]
    failed_client_ids: List[str]
    status: str

from app.models.sync import SyncEvent
import dateutil.parser

@router.post("/events", response_model=SyncResponse)
def sync_events(
    batch: SyncBatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Receives a batch of offline events and processes them.
    Implements idempotency by checking client_id.
    """
    synced = []
    failed = []
    
    for event in batch.events:
        try:
            # Idempotency check
            existing = db.query(SyncEvent).filter(SyncEvent.client_id == event.client_id).first()
            if existing:
                synced.append(event.client_id)
                continue
                
            try:
                client_time = dateutil.parser.isoparse(event.created_at)
            except Exception:
                client_time = datetime.utcnow()
                
            new_sync = SyncEvent(
                user_id=current_user.id,
                client_id=event.client_id,
                event_type=event.event_type,
                payload=event.payload,
                client_created_at=client_time,
                server_synced_at=datetime.utcnow()
            )
            db.add(new_sync)
            db.commit()
            
            # Additional processing based on event_type could go here.
            
            synced.append(event.client_id)
        except Exception as e:
            db.rollback()
            print(f"Error syncing event {event.client_id}: {e}")
            failed.append(event.client_id)
            
    return SyncResponse(
        synced_client_ids=synced,
        failed_client_ids=failed,
        status="completed" if not failed else "partial"
    )
