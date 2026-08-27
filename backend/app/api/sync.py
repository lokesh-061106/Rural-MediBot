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
            
            # Additional processing based on event_type
            if event.event_type == 'chat_query':
                from app.memory.persistence import MemoryService
                p = event.payload
                conv_id = p.get('conversation_id')
                if not conv_id:
                    conv = MemoryService.create_conversation(db, current_user.id, p.get('query', '')[:50], p.get('language', 'en'))
                    conv_id = conv.id
                else:
                    conv = MemoryService.get_conversation(db, conv_id, current_user.id)
                    if not conv:
                        # Fallback if invalid
                        conv = MemoryService.create_conversation(db, current_user.id, p.get('query', '')[:50], p.get('language', 'en'))
                        conv_id = conv.id

                # Save the user query
                MemoryService.save_message(
                    db,
                    conversation_id=conv_id,
                    role="user",
                    content=p.get('query'),
                    language=p.get('language', 'en')
                )
                
                # Save the offline assistant response
                is_emergency = p.get('is_emergency', False)
                risk_level = "RED" if is_emergency else "low"
                reason_code = "offline_emergency" if is_emergency else "offline_fallback"
                
                # We need to grab the offline responses since they were generated on client
                # or we can reconstruct them. It's better to store what the client showed.
                # Since the client didn't send the exact assistant text, we use defaults based on status
                if is_emergency:
                    asst_content = "🚨 **MEDICAL EMERGENCY DETECTED** 🚨\nPlease call your local emergency services (like 108 in India) immediately or go to the nearest emergency room. I am currently offline and cannot provide dynamic medical assistance."
                else:
                    asst_content = "I am currently offline and do not have verified information for this question. Please reconnect to the internet to continue with the AI health assistant, or contact a health professional if you need immediate guidance."
                    
                MemoryService.save_message(
                    db,
                    conversation_id=conv_id,
                    role="assistant",
                    content=asst_content,
                    language=p.get('language', 'en'),
                    risk_level=risk_level,
                    reason_code=reason_code
                )
            
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
