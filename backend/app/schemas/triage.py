from pydantic import BaseModel, Field

class TriageResult(BaseModel):
    risk_level: str = Field(description="Must be GREEN, YELLOW, ORANGE, or RED")
    confidence: str = Field(default="high", description="high, medium, low")
    reason: str = Field(description="Human readable explanation")
    reason_code: str = Field(description="Machine readable reason code")
    emergency: bool = Field(default=False)
    requires_human_care: bool = Field(default=False)
    should_bypass_rag: bool = Field(default=False)
