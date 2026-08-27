"use client";
import { useState, useEffect, useRef } from "react";
import AppLayout from "@/components/AppLayout";
import { VoiceService } from "@/lib/services/VoiceService";

const SAMPLE_MESSAGES = [
  { role: "model", content: "👋 Hello! I'm your customizable AI assistant. I will act based on the role you define below. I support **English**, **Hindi (हिंदी)**, **Marathi (मराठी)**, **Tamil (தமிழ்)**, and **Odia (ଓଡ଼ିଆ)**.\n\n⚠️ I will ONLY answer questions relevant to my assigned role." },
];

export default function ChatPage() {
  const [messages, setMessages] = useState(SAMPLE_MESSAGES);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [lang, setLang] = useState("en");
  const [roleDescription, setRoleDescription] = useState("Software Engineer");
  const [listening, setListening] = useState(false);
  const [accessibilityMode, setAccessibilityMode] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    const handleStorageChange = () => {
      setLang(localStorage.getItem("medibot_lang") || "en");
    };
    handleStorageChange();
    window.addEventListener("storage", handleStorageChange);
    // Periodically check (simple way since AppLayout sets it without event)
    const interval = setInterval(handleStorageChange, 1000);
    return () => {
      window.removeEventListener("storage", handleStorageChange);
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (text = input) => {
    if (!text.trim() || loading) return;
    const userMsg = { role: "user", content: text };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);

    try {
      if (typeof navigator !== 'undefined' && !navigator.onLine) {
        // --- OFFLINE MODE ---
        const { analyzeQueryOffline, getOfflineEmergencyResponse, getOfflineFallbackResponse } = await import('../../lib/offline-triage');
        const { queueChatMessage } = await import('../../lib/db');
        
        const triageResult = analyzeQueryOffline(text);
        
        if (triageResult.isEmergency) {
          const content = getOfflineEmergencyResponse();
          setMessages((m) => [...m, { role: "model", content, is_emergency: true }]);
          if (accessibilityMode) VoiceService.speak(content, lang);
        } else {
          // Queue the message to be synced later
          await queueChatMessage({ query: text, thread_id: "default_user_1", roleDescription });
          const content = getOfflineFallbackResponse();
          setMessages((m) => [...m, { role: "model", content }]);
          if (accessibilityMode) VoiceService.speak(content, lang);
        }
      } else {
        // --- ONLINE MODE ---
        const history = messages.slice(1).map((m) => ({ role: m.role, content: m.content }));
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: text, history, language: lang, roleDescription }),
        });
        const data = await res.json();
        const content = data.response || "Sorry, I couldn't process that.";
        setMessages((m) => [...m, { 
          role: "model", 
          content: content,
          sources: data.sources || [],
          is_emergency: data.is_emergency,
          risk_level: data.risk_level,
          recommended_facility: data.recommended_facility
        }]);
        if (accessibilityMode || listening) {
           VoiceService.speak(content, lang);
        }
      }

      // Save to localStorage (simple history)
      const saved = JSON.parse(localStorage.getItem("medibot_chats") || "[]");
      saved.push({ date: new Date().toISOString(), symptoms: text });
      localStorage.setItem("medibot_chats", JSON.stringify(saved.slice(-20)));
    } catch {
      setMessages((m) => [...m, { role: "model", content: "⚠️ Connection error. Please try again." }]);
    } finally { setLoading(false); }
  };

  const startVoice = () => {
    setListening(true);
    VoiceService.startListening(
      lang,
      (transcript, isFinal) => {
        setInput(transcript);
        if (isFinal) {
           setTimeout(() => {
             setListening(false);
             sendMessage(transcript);
           }, 500);
        }
      },
      (err) => {
        console.error(err);
        setListening(false);
        alert(err.message || "Failed to start voice recognition.");
      },
      () => {
        setListening(false);
      }
    );
  };

  const stopVoice = () => {
    VoiceService.stopListening();
    setListening(false);
  };

  const formatMessage = (text) => {
    return text
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/^#{1,3}\s(.+)$/gm, "<h4 class='font-bold text-sky-400 mt-3 mb-1'>$1</h4>")
      .replace(/\n/g, "<br/>");
  };

  const quickSymptoms = ["Tell me a joke", "Explain a concept", "Give me advice", "Write some code", "Analyze this"];

  const texts = {
    en: { tap: "TAP TO SPEAK", typing: "Or type your question...", ai: "Assistant" },
    hi: { tap: "बोलने के लिए टैप करें", typing: "या अपना सवाल टाइप करें...", ai: "सहायक" },
    mr: { tap: "बोलण्यासाठी टॅप करा", typing: "किंवा तुमचा प्रश्न टाइप करा...", ai: "सहाय्यक" },
    ta: { tap: "பேச தட்டவும்", typing: "அல்லது உங்கள் கேள்வியை தட்டச்சு செய்யவும்...", ai: "உதவியாளர்" },
    or: { tap: "କହିବା ପାଇଁ ଟ୍ୟାପ୍ କରନ୍ତୁ", typing: "କିମ୍ବା ଆପଣଙ୍କର ପ୍ରଶ୍ନ ଟାଇପ୍ କରନ୍ତୁ...", ai: "ସହାୟକ" }
  };
  const t = texts[lang] || texts.en;

  return (
    <AppLayout>
      <div className={`flex flex-col mx-auto ${accessibilityMode ? 'max-w-3xl h-[calc(100vh-8rem)] text-lg' : 'max-w-4xl h-[calc(100vh-10rem)]'}`}>
        {/* Header */}
        <div className="flex flex-col mb-4 gap-2">
          <div className="flex items-center justify-between">
            <div>
              <h1 className={`${accessibilityMode ? 'text-3xl' : 'text-2xl'} font-black`}>🤖 AI Role-based Assistant</h1>
              <p className="text-slate-400 text-sm">Powered by Google Gemini / Groq</p>
            </div>
            <div className="flex gap-2 items-center">
              <label className="flex items-center gap-2 text-slate-300 text-sm cursor-pointer">
                <input 
                   type="checkbox" 
                   checked={accessibilityMode} 
                   onChange={(e) => setAccessibilityMode(e.target.checked)}
                   className="w-4 h-4 rounded bg-slate-800 border-slate-600 text-sky-500"
                />
                Rural Accessibility Mode
              </label>
              <button onClick={() => setMessages(SAMPLE_MESSAGES)} className="glass px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white transition-all">Clear</button>
            </div>
          </div>
          {!accessibilityMode && (
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-slate-300">Bot Role:</span>
            <input 
              type="text" 
              className="input-field flex-1 max-w-md text-sm py-1"
              value={roleDescription}
              onChange={(e) => setRoleDescription(e.target.value)}
              placeholder="e.g. Math Teacher, Software Engineer, Fitness Coach"
            />
          </div>
          )}
        </div>

        {/* Quick actions */}
        {!accessibilityMode && (
        <div className="flex gap-2 flex-wrap mb-4">
          {quickSymptoms.map((s) => (
            <button key={s} onClick={() => sendMessage(s)}
              className="glass px-3 py-1.5 rounded-full text-xs text-slate-300 hover:text-white hover:bg-sky-500/20 hover:border-sky-500/30 border border-transparent transition-all">
              {s}
            </button>
          ))}
        </div>
        )}

        {/* Chat messages */}
        <div className={`flex-1 glass-dark rounded-2xl p-4 overflow-y-auto space-y-4 mb-4 ${accessibilityMode ? 'border-2 border-slate-700' : ''}`}>
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] ${msg.role === "user"
                ? "bg-gradient-to-r from-sky-600 to-blue-600 rounded-2xl rounded-tr-sm px-4 py-3 text-white"
                : "glass rounded-2xl rounded-tl-sm px-4 py-3 text-slate-200"} ${accessibilityMode ? 'text-lg' : 'text-sm'}`}>
                
                {msg.role === "model" && (
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 bg-gradient-to-br from-sky-400 to-blue-600 rounded-full flex items-center justify-center text-xs font-bold text-white">AI</div>
                      <span className="text-xs text-sky-400 font-semibold">{t.ai}</span>
                    </div>
                    {VoiceService.isSupported() && (
                      <button onClick={() => VoiceService.speak(msg.content, lang)} className="text-slate-400 hover:text-white" title="Read aloud">
                        🔊
                      </button>
                    )}
                  </div>
                )}
                
                <div dangerouslySetInnerHTML={{ __html: formatMessage(msg.content) }} className="leading-relaxed" />
                
                {/* Explainable AI: Sources */}
                {!accessibilityMode && msg.sources && msg.sources.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-700/50">
                    <p className="text-xs font-semibold text-sky-400 mb-2 flex items-center gap-1">
                      Verified Medical Sources
                    </p>
                    <div className="flex flex-col gap-2">
                      {msg.sources.map((src, idx) => (
                        <div key={idx} className="bg-slate-800/50 rounded-lg p-2 text-[11px]">
                          <div className="flex justify-between items-center mb-1">
                            <span className="text-slate-300 font-medium truncate">{src.source}</span>
                            <span className={`px-1.5 py-0.5 rounded text-[10px] ${src.relevance_score > 3 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}`}>
                              Confidence: {src.relevance_score.toFixed(1)}
                            </span>
                          </div>
                          <p className="text-slate-500 line-clamp-2 italic">"{src.content}"</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Emergency & Facility Recommendation */}
                {msg.is_emergency && (
                  <div className="mt-4 p-4 bg-red-900/60 border-2 border-red-500/80 rounded-xl">
                    <div className={`flex items-center text-red-400 font-bold ${accessibilityMode ? 'text-xl mb-3' : 'mb-2'}`}>
                      <span className="mr-2">🚨</span> POSSIBLE EMERGENCY
                    </div>
                    <p className={`${accessibilityMode ? 'text-sm' : 'text-xs'} text-red-200 mb-4`}>Your reported symptoms may require urgent medical evaluation.</p>
                    <div className="flex flex-col gap-3">
                      <a href="tel:108" className={`bg-red-600 hover:bg-red-700 text-white text-center rounded-lg font-bold transition ${accessibilityMode ? 'py-4 text-lg' : 'py-2 text-sm'}`}>Call Ambulance (108)</a>
                      <a href="/facilities?emergency=true" className={`bg-slate-800 hover:bg-slate-700 border border-slate-600 text-white text-center rounded-lg font-medium transition ${accessibilityMode ? 'py-4 text-lg' : 'py-2 text-sm'}`}>Find Nearest Emergency Facility</a>
                    </div>
                  </div>
                )}
                
                {!msg.is_emergency && msg.recommended_facility && (
                  <div className="mt-4 p-3 bg-blue-900/40 border border-blue-500/40 rounded-xl">
                    <div className="flex items-center text-blue-400 font-bold mb-2">
                      <span className="mr-2">🏥</span> Recommended: {msg.recommended_facility}
                    </div>
                    <p className={`${accessibilityMode ? 'text-sm' : 'text-[11px]'} text-blue-200 mb-3`}>Based on your {msg.risk_level} risk level, we recommend visiting a {msg.recommended_facility}.</p>
                    <a href={`/facilities?type=${encodeURIComponent(msg.recommended_facility)}`} className={`block w-full bg-blue-600 hover:bg-blue-700 text-white text-center rounded-lg font-medium transition ${accessibilityMode ? 'py-3 text-base' : 'py-1.5 text-xs'}`}>
                      Find Nearby {msg.recommended_facility}
                    </a>
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="glass rounded-2xl rounded-tl-sm px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1">
                    {[0, 1, 2].map((i) => (
                      <div key={i} className="w-2 h-2 bg-sky-400 rounded-full animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                    ))}
                  </div>
                  <span className="text-xs text-slate-400">Assistant is analyzing...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input Area */}
        {accessibilityMode ? (
          <div className="flex flex-col gap-3">
            <button 
              onClick={listening ? stopVoice : startVoice}
              className={`w-full py-8 rounded-2xl flex flex-col items-center justify-center transition-all ${listening ? "bg-red-500/20 border-2 border-red-500 text-red-400 animate-pulse" : "bg-sky-600 hover:bg-sky-500 text-white shadow-lg"}`}
            >
              <span className="text-4xl mb-2">🎤</span>
              <span className="font-bold text-xl tracking-wide">{listening ? "LISTENING..." : t.tap}</span>
            </button>
            <div className="flex gap-2">
              <input
                className="input-field flex-1 text-lg py-3"
                placeholder={t.typing}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
              />
              <button onClick={() => sendMessage()} disabled={loading || !input.trim()} className="btn-primary px-6 font-bold disabled:opacity-50 text-lg">
                Send
              </button>
            </div>
          </div>
        ) : (
          <div className="flex gap-2">
            <button onClick={listening ? stopVoice : startVoice}
              className={`glass p-3 rounded-xl transition-all ${listening ? "bg-red-500/20 border-red-500/50 text-red-400 animate-pulse" : "text-slate-400 hover:text-sky-400 hover:border-sky-500/30"} border border-transparent`}
              title={listening ? "Stop listening" : "Voice input"}>
              🎤
            </button>
            <input
              className="input-field flex-1"
              placeholder={listening ? "🎙️ Listening..." : t.typing}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
            />
            <button onClick={() => sendMessage()} disabled={loading || !input.trim()} className="btn-primary px-5 py-3 disabled:opacity-50">
              Send
            </button>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
