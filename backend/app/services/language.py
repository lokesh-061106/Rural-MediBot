from typing import Optional

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
    "ta": "Tamil"
}

def detect_language(text: str) -> str:
    """
    Basic deterministic language detection fallback.
    Production systems might use a fastText model or similar, but for M4.3 base architecture,
    we rely on the client providing the language explicitly. If missing, default to English.
    """
    return "en"

def normalize_text(text: str, language: str) -> str:
    """
    Normalize text based on language rules if necessary.
    """
    if not text:
        return ""
    return text.strip()

def prepare_for_triage(text: str, language: str) -> str:
    """
    Prepare text for triage. 
    In future, could involve translation to English for better LLM reasoning,
    but for now, pass through as LLMs handle cross-lingual triage natively.
    """
    return normalize_text(text, language)

def prepare_for_generation(text: str, language: str) -> str:
    """
    Prepare text for generation.
    """
    return normalize_text(text, language)

def format_response(text: str, language: str) -> str:
    """
    Format output response for the specified language.
    """
    if not text:
        return ""
    
    # Simple fallback check: If asked for non-English but responded purely in English,
    # could theoretically catch it here, but LLM usually follows instructions.
    return text
