// Deterministic Emergency Regex Matching
// Prioritizes safety routing, NOT diagnosis.

const EMERGENCY_PATTERNS = [
  // English Patterns
  /\b(heart attack|stroke|seizure|choking|unconscious|not breathing|severe bleeding|chest pain|suicide|kill myself|poisoning|snake bite)\b/i,
  /\b(can't breathe|difficulty breathing|shortness of breath)\b/i,
  /\b(severe allergic|anaphylaxis|swollen throat|swelling throat)\b/i,
  /\b(head injury|severe burn|heavy bleeding)\b/i,
  
  // Hindi Patterns (Roman & Devanagari basics)
  /\b(dil ka daura|saans lene mein dikkat|behosh|chati mein dard|khoon nikal raha|zehar|saanp ne kata)\b/i,
  /(दिल का दौरा|सांस लेने में दिक्कत|सांस फूलना|बेहोश|छाती में दर्द|सीने में दर्द|बहुत खून|ज़हर|सांप ने काटा)/,

  // Marathi Patterns
  /\b(hruday vikar|shwas ghyayla traas|beshuddha|chhatit dukhate|rakta srav|vish|saap chavla)\b/i,
  /(हृदयविकार|श्वास घ्यायला त्रास|बेशुद्ध|छातीत दुखते|रक्तस्राव|विष|साप चावला)/,

  // Tamil Patterns
  /\b(nenju vali|moochu vida siramam|mayakkam|ratham varuthu|visham|pambu kadichuduchu)\b/i,
  /(மாரடைப்பு|மூச்சு திணறல்|மயக்கம்|நெஞ்சு வலி|ரத்தம்|விஷம்|பாம்பு)/
];

export function analyzeQueryOffline(query) {
  if (!query) return { isEmergency: false, category: 'general' };
  
  for (let pattern of EMERGENCY_PATTERNS) {
    if (pattern.test(query)) {
      return { 
        isEmergency: true, 
        category: 'emergency',
        matchedPattern: pattern.toString()
      };
    }
  }

  // If no emergency detected, fallback to general/unsupported offline state
  return { 
    isEmergency: false, 
    category: 'unknown'
  };
}

export function getOfflineEmergencyResponse() {
  return "🚨 **MEDICAL EMERGENCY DETECTED** 🚨\nPlease call your local emergency services (like 108 in India) immediately or go to the nearest emergency room. I am currently offline and cannot provide dynamic medical assistance.";
}

export function getOfflineFallbackResponse() {
  return "I am currently offline and do not have verified information for this question. Please reconnect to the internet to continue with the AI health assistant, or contact a health professional if you need immediate guidance.";
}
