/**
 * VoiceService for M4.3 (Rural Voice + Multilingual Health Assistant).
 * Implements Web Speech API for STT and TTS.
 */
export class VoiceService {
  static recognition = null;
  static synthesis = typeof window !== 'undefined' ? window.speechSynthesis : null;
  static _isListening = false;

  static getLangCode(lang) {
    const map = {
      en: 'en-IN',
      hi: 'hi-IN',
      mr: 'mr-IN',
      ta: 'ta-IN'
    };
    return map[lang] || 'en-IN';
  }

  static isSupported() {
    return typeof window !== 'undefined' && 
           ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window);
  }

  static startListening(lang = 'en', onResult, onError, onEnd) {
    if (!this.isSupported()) {
      if (onError) onError(new Error("Voice input not supported in this browser."));
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (this.recognition) {
      this.recognition.stop();
    }
    
    this.recognition = new SpeechRecognition();
    this.recognition.continuous = false;
    this.recognition.interimResults = true;
    this.recognition.lang = this.getLangCode(lang);

    this.recognition.onstart = () => {
      this._isListening = true;
    };

    this.recognition.onresult = (e) => {
      const transcript = Array.from(e.results)
        .map((r) => r[0].transcript)
        .join("");
      if (onResult) onResult(transcript, e.results[0].isFinal);
    };

    this.recognition.onerror = (e) => {
      this._isListening = false;
      if (onError) onError(e);
    };

    this.recognition.onend = () => {
      this._isListening = false;
      if (onEnd) onEnd();
    };

    try {
      this.recognition.start();
    } catch (e) {
      this._isListening = false;
      if (onError) onError(e);
    }
  }

  static stopListening() {
    if (this.recognition) {
      this.recognition.stop();
      this.recognition = null;
    }
    this._isListening = false;
  }

  static isListening() {
    return this._isListening;
  }

  static speak(text, lang = 'en') {
    if (!this.synthesis) return;
    
    // Stop any ongoing speech
    this.synthesis.cancel();

    // Remove markdown asterisks, hashes, and HTML tags for speech
    const cleanText = text.replace(/[*_#]/g, '').replace(/<[^>]*>?/gm, '');
    
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = this.getLangCode(lang);
    
    // Try to find a local voice that matches the language
    const voices = this.synthesis.getVoices();
    const targetLangCode = this.getLangCode(lang);
    const voice = voices.find(v => v.lang.replace('_', '-').toLowerCase() === targetLangCode.toLowerCase());
    
    if (voice) {
      utterance.voice = voice;
    } else {
      // Fallback to broader language match
      const fallbackVoice = voices.find(v => v.lang.startsWith(lang));
      if (fallbackVoice) utterance.voice = fallbackVoice;
    }

    // Slightly slower rate for rural accessibility / clarity
    utterance.rate = 0.9;
    
    this.synthesis.speak(utterance);
  }

  static stopSpeaking() {
    if (this.synthesis) {
      this.synthesis.cancel();
    }
  }

  static isSpeaking() {
    return this.synthesis ? this.synthesis.speaking : false;
  }
}
