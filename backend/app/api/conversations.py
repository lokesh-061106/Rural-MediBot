from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.memory import Conversation, Message
from app.models.user import User
from app.api.deps import get_current_active_user
from app.schemas.memory import ConversationOut, ConversationCreate, ConversationUpdate, MessageOut, ConversationWithMessages
from app.memory.persistence import MemoryService

router = APIRouter()

@router.post("/", response_model=ConversationOut)
def create_conversation(
    conv_in: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return MemoryService.create_conversation(db, current_user.id, conv_in.title or "New Conversation", conv_in.language)

@router.get("/", response_model=List[ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return MemoryService.list_user_conversations(db, current_user.id)

@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    conv = MemoryService.get_conversation(db, conversation_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv

@router.patch("/{conversation_id}", response_model=ConversationOut)
def update_conversation(
    conversation_id: int,
    conv_in: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    conv = MemoryService.get_conversation(db, conversation_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conv_in.title is not None:
        conv.title = conv_in.title
    if conv_in.language is not None:
        conv.language = conv_in.language
    if conv_in.status is not None:
        conv.status = conv_in.status
        
    db.commit()
    db.refresh(conv)
    return conv

@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    success = MemoryService.delete_conversation(db, conversation_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return None

@router.get("/{conversation_id}/messages", response_model=List[MessageOut])
def get_conversation_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    conv = MemoryService.get_conversation(db, conversation_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    return MemoryService.get_conversation_messages(db, conversation_id)

