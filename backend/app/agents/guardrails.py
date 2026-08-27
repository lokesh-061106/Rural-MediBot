import re
from typing import Optional, Dict, Any

# Phase 8: Multilingual Deterministic Emergency Recognition
# Maintainable phrase/category structure (no huge arbitrary database)
EMERGENCY_RULES = {
    "EMERGENCY_BREATHING_DIFFICULTY": [
        r"\b(can'?t breathe|difficulty breathing|shortness of breath|choking)\b", # EN
        r"(saans lene mein dikkat|saans phoolna)", # HI romanized
        r"(सांस लेने में दिक्कत|सांस फूलना)", # HI devanagari
        r"(shwas ghyayla traas)", # MR romanized
        r"(श्वास घ्यायला त्रास)", # MR
        r"(moochu vida siramam|moochu thinarel)", # TA romanized
        r"(மூச்சு திணறல்)", # TA
    ],
    "EMERGENCY_CHEST_PAIN": [
        r"\b(heart attack|severe chest pain)\b", # EN
        r"(dil ka daura|chati mein dard|seene mein dard)", # HI romanized
        r"(दिल का दौरा|छाती में दर्द|सीने में दर्द)", # HI
        r"(hruday vikar|chhatit dukhate)", # MR romanized
        r"(हृदयविकार|छातीत दुखते)", # MR
        r"(nenju vali|maradaippu)", # TA romanized
        r"(மாரடைப்பு|நெஞ்சு வலி)", # TA
    ],
    "EMERGENCY_UNCONSCIOUS": [
        r"\b(unconscious|not breathing|unresponsive|passed out)\b",
        r"(behosh)", # HI/MR romanized
        r"(बेहोश|बेशुद्ध)", # HI/MR
        r"(mayakkam)", # TA
        r"(மயக்கம்)", # TA
    ],
    "EMERGENCY_BLEEDING": [
        r"\b(severe bleeding|heavy bleeding|bleeding heavily|uncontrolled bleeding)\b",
        r"(bahut khoon nikal raha|rakta srav)", 
        r"(बहुत खून|रक्तस्राव)",
        r"(ratham varuthu)",
        r"(ரத்தம்)",
    ],
    "EMERGENCY_TRAUMA_POISON": [
        r"\b(poisoning|overdose|snake bite|severe burn|head injury|suicide|kill myself)\b",
        r"(zehar|saanp ne kata|vish|saap chavla)",
        r"(ज़हर|सांप ने काटा|विष|साप चावला)",
        r"(visham|pambu kadichuduchu)",
        r"(விஷம்|பாம்பு)",
    ],
    "EMERGENCY_STROKE_SEIZURE": [
        r"\b(stroke|seizure|paralyzed|face drooping)\b"
    ],
    "EMERGENCY_ANAPHYLAXIS": [
        r"\b(severe allergic|anaphylaxis|swollen throat|swelling throat)\b"
    ]
}

def analyze_deterministic_safety(query: str) -> Optional[Dict[str, Any]]:
    """
    Executes before LLM. If a clear emergency signal is found, returns RED payload.
    """
    if not query:
        return None
        
    query_lower = query.lower()
    
    for reason_code, patterns in EMERGENCY_RULES.items():
        for pattern in patterns:
            # use re.IGNORECASE just to be safe, though query is lower
            if re.search(pattern, query_lower, re.IGNORECASE):
                return {
                    "risk_level": "RED",
                    "emergency": True,
                    "requires_human_care": True,
                    "should_bypass_rag": True,
                    "reason_code": reason_code,
                    "reason": "Deterministic safety rule triggered due to potential life-threatening symptoms."
                }
                
    return None
