from sqlalchemy.orm import Session
from app.models.memory import Conversation, Message, PatientContext
from app.schemas.memory import ConversationCreate, ConversationUpdate, PatientContextUpdate

class MemoryService:
    @staticmethod
    def create_conversation(db: Session, user_id: int, title: str, language: str) -> Conversation:
        conv = Conversation(user_id=user_id, title=title, language=language)
        db.add(conv)
        db.commit()
        db.refresh(conv)
        return conv

    @staticmethod
    def get_conversation(db: Session, conversation_id: int, user_id: int) -> Conversation:
        return db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.status != "deleted"
        ).first()

    @staticmethod
    def list_user_conversations(db: Session, user_id: int):
        return db.query(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.status != "deleted"
        ).order_by(Conversation.updated_at.desc()).all()

    @staticmethod
    def delete_conversation(db: Session, conversation_id: int, user_id: int) -> bool:
        conv = MemoryService.get_conversation(db, conversation_id, user_id)
        if conv:
            conv.status = "deleted"
            db.commit()
            return True
        return False

    @staticmethod
    def save_message(db: Session, conversation_id: int, role: str, content: str, language: str = None, risk_level: str = None, reason_code: str = None) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            language=language,
            risk_level=risk_level,
            reason_code=reason_code
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        
        # Also update conversation updated_at
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conv:
            db.add(conv) # triggers onupdate
            db.commit()
            
        return msg

    @staticmethod
    def get_conversation_messages(db: Session, conversation_id: int, limit: int = None):
        query = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at.desc())
        if limit:
            query = query.limit(limit)
        messages = query.all()
        return list(reversed(messages)) # return chronological

    @staticmethod
    def get_patient_context(db: Session, user_id: int) -> PatientContext:
        ctx = db.query(PatientContext).filter(PatientContext.user_id == user_id).first()
        if not ctx:
            ctx = PatientContext(user_id=user_id)
            db.add(ctx)
            db.commit()
            db.refresh(ctx)
        return ctx

    @staticmethod
    def update_patient_context(db: Session, user_id: int, ctx_in: PatientContextUpdate) -> PatientContext:
        ctx = MemoryService.get_patient_context(db, user_id)
        
        ctx.age = ctx_in.age
        ctx.sex = ctx_in.sex
        ctx.known_conditions = ctx_in.known_conditions
        ctx.allergies = ctx_in.allergies
        ctx.current_medications = ctx_in.current_medications
        ctx.relevant_notes = ctx_in.relevant_notes
        
        db.commit()
        db.refresh(ctx)
        return ctx

