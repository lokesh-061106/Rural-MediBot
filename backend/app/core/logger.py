import logging
import json
import uuid
from datetime import datetime
from contextvars import ContextVar

# A context variable to hold a request ID for tracing
request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="")

class PrivacySafeJSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings for observability while explicitly 
    preventing sensitive fields from being logged.
    """
    SENSITIVE_KEYS = {"password", "token", "jwt", "content", "query", "history", "patient_context", "raw", "audio"}
    
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": request_id_ctx_var.get(),
            "message": record.getMessage()
        }
        
        if hasattr(record, "observability_data"):
            safe_data = {}
            for k, v in record.observability_data.items():
                # Block sensitive keys
                if any(sensitive in k.lower() for sensitive in self.SENSITIVE_KEYS):
                    safe_data[k] = "[REDACTED]"
                else:
                    safe_data[k] = v
            log_obj["metadata"] = safe_data
            
        return json.dumps(log_obj)

def setup_logger():
    logger = logging.getLogger("medibot_observability")
    logger.setLevel(logging.INFO)
    
    # Prevent adding multiple handlers during reloads
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setFormatter(PrivacySafeJSONFormatter())
        logger.addHandler(ch)
        
    return logger

observability_logger = setup_logger()

