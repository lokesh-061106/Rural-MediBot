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
  /(மாரடைப்பு|மூச்சு திணறல்|மயக்கம்|நெஞ்சு வலி|ரத்தம்|விஷம்|பாம்பு)/,
];

const OFFLINE_GUIDANCE = [
  {
    category: "fever",
    patterns:
      /\b(fever|temperature|hot body|pyrexia|bukhar|बुखार|ताप|காய்ச்சல்)\b/i,
    response:
      "For a fever: rest, drink small amounts of water or oral rehydration solution, and wear light clothing. Check your temperature if possible. Seek medical care urgently for trouble breathing, confusion, stiff neck, seizure, dehydration, a fever in a baby under 3 months, or a fever lasting more than 3 days. Do not give aspirin to children.\n\nDisclaimer: This is general offline guidance, not a diagnosis or a prescription.",
  },
  {
    category: "cold",
    patterns:
      /\b(cold|common cold|runny nose|blocked nose|stuffy nose|sneezing|सर्दी|जुकाम|सर्दी खोकला|சளி)\b/i,
    response:
      "For a common cold: rest, drink fluids, use warm liquids, and try saline nasal drops or steam from a safe distance. Avoid antibiotics unless prescribed by a clinician. Seek care for breathing difficulty, chest pain, blue lips, severe weakness, or symptoms that worsen or do not improve after about 10 days.\n\nDisclaimer: This is general offline guidance, not a diagnosis or a prescription.",
  },
  {
    category: "cough",
    patterns: /\b(cough(?:ing)?|खांसी|खोकला|இருமல்)\b/i,
    response:
      "For a cough: drink fluids, rest, avoid smoke and dust, and use honey only for people older than 1 year. Seek medical care for difficulty breathing, coughing blood, chest pain, high fever, or a cough lasting more than 3 weeks.\n\nDisclaimer: This is general offline guidance, not a diagnosis or a prescription.",
  },
  {
    category: "headache",
    patterns:
      /\b(headache|head pain|head hurts|migraine|सिरदर्द|डोकेदुखी|தலைவலி)\b/i,
    response:
      "For a mild headache: rest in a quiet place, drink water, eat if you have missed a meal, and limit bright screens. Seek urgent care for a sudden worst-ever headache, weakness, confusion, fainting, stiff neck, vision loss, head injury, or repeated vomiting.\n\nDisclaimer: This is general offline guidance, not a diagnosis or a prescription.",
  },
  {
    category: "stomach",
    patterns:
      /\b(vomiting|vomit|nausea|diarrhea|loose motion|loose motions|दस्त|उल्टी|मळमळ|जुलाब|வாந்தி|வயிற்றுப்போக்கு)\b/i,
    response:
      "For vomiting or diarrhea: take frequent small sips of oral rehydration solution, continue light food as tolerated, and wash hands. Seek urgent care for blood, severe belly pain, confusion, very little urine, inability to keep fluids down, or signs of dehydration.\n\nDisclaimer: This is general offline guidance, not a diagnosis or a prescription.",
  },
  {
    category: "pain",
    patterns:
      /\b(back pain|body pain|joint pain|toothache|दर्द|अंगदुखी|முதுகுவலி)\b/i,
    response:
      "For mild muscle or joint pain: rest the affected area, avoid heavy activity, and use a wrapped cool or warm pack for short periods. Seek care for severe pain, swelling or redness, numbness or weakness, injury, or pain with fever.\n\nDisclaimer: This is general offline guidance, not a diagnosis or a prescription.",
  },
];

export function analyzeQueryOffline(query) {
  if (!query)
    return { isEmergency: false, riskLevel: "GREEN", category: "general" };

  for (let pattern of EMERGENCY_PATTERNS) {
    if (pattern.test(query)) {
      return {
        isEmergency: true,
        riskLevel: "RED",
        category: "emergency",
        matchedPattern: pattern.toString(),
        reasonCode: "OFFLINE_EMERGENCY_MATCH",
      };
    }
  }

  const guidance = OFFLINE_GUIDANCE.find((item) => item.patterns.test(query));

  return {
    isEmergency: false,
    riskLevel: guidance ? "YELLOW" : "GREEN",
    category: guidance?.category || "general",
    reasonCode: guidance ? "OFFLINE_SYMPTOM_GUIDANCE" : "OFFLINE_GENERAL",
  };
}

export function getOfflineEmergencyResponse() {
  return "🚨 **MEDICAL EMERGENCY DETECTED** 🚨\nPlease call your local emergency services (like 108 in India) immediately or go to the nearest emergency room. I am currently offline and cannot provide dynamic medical assistance.";
}

export function getOfflineFallbackResponse() {
  return "I am offline, but I can still help with basic safety guidance. Tell me the main symptom, how long it has been present, the person's age, and any warning signs. For severe breathing trouble, chest pain, unconsciousness, heavy bleeding, or a seizure, call 108 immediately.\n\nDisclaimer: Offline guidance cannot diagnose illness or replace a healthcare professional.";
}

export function getOfflineResponse(query) {
  if (!query) return getOfflineFallbackResponse();
  if (analyzeQueryOffline(query).isEmergency)
    return getOfflineEmergencyResponse();
  const guidance = OFFLINE_GUIDANCE.find((item) => item.patterns.test(query));
  return guidance?.response || getOfflineFallbackResponse();
}
