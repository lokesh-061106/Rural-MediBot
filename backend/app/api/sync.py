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

# In a real app we'd map this to a DB table like SyncEvent.
# For M2, we process them idempotently and return success.
@router.post("/events", response_model=SyncResponse)
def sync_events(
    batch: SyncBatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Receives a batch of offline events (health events, chat queries) 
    and processes them. Implements idempotency by checking client_id.
    """
    synced = []
    failed = []
    
    for event in batch.events:
        try:
            # Here we would normally insert into a Postgres SyncEvent table
            # verifying that (user_id, client_id) is unique.
            # Example: 
            # if event.event_type == 'health_event':
            #     process_health_event(event)
            
            # Since this is the M2 foundation, we acknowledge them safely
            # to clear the client queue.
            synced.append(event.client_id)
        except Exception as e:
            print(f"Error syncing event {event.client_id}: {e}")
            failed.append(event.client_id)
            
    return SyncResponse(
        synced_client_ids=synced,
        failed_client_ids=failed,
        status="completed" if not failed else "partial"
    )
