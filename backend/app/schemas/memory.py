from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime

class MessageBase(BaseModel):
    role: str
    content: str
    language: Optional[str] = None
    risk_level: Optional[str] = None
    reason_code: Optional[str] = None

class MessageOut(MessageBase):
    id: int
    conversation_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ConversationBase(BaseModel):
    title: Optional[str] = None
    language: str = "en"

class ConversationCreate(ConversationBase):
    pass

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    language: Optional[str] = None
    status: Optional[str] = None

class ConversationOut(ConversationBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ConversationWithMessages(ConversationOut):
    messages: List[MessageOut] = []

class PatientContextBase(BaseModel):
    age: Optional[int] = None
    sex: Optional[str] = None
    known_conditions: List[str] = []
    allergies: List[str] = []
    current_medications: List[str] = []
    relevant_notes: Optional[str] = None

class PatientContextUpdate(PatientContextBase):
    pass

class PatientContextOut(PatientContextBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
