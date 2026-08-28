"use client";
import { useState, useEffect, useRef } from "react";
import AppLayout from "@/components/AppLayout";
import { VoiceService } from "@/lib/services/VoiceService";
import { useLocation } from "@/hooks/useLocation";

const SAMPLE_MESSAGES = [
  {
    role: "model",
    content:
      "👋 Hello! I'm your customizable AI assistant. I will act based on the role you define below. I support **English**, **Hindi (हिंदी)**, **Marathi (मराठी)**, **Tamil (தமிழ்)**, and **Odia (ଓଡ଼ିଆ)**.\n\n⚠️ I will ONLY answer questions relevant to my assigned role.",
  },
];

export default function ChatPage() {
  const [messages, setMessages] = useState(SAMPLE_MESSAGES);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [lang, setLang] = useState("en");
  const [roleDescription, setRoleDescription] = useState("Software Engineer");
  const [listening, setListening] = useState(false);
  const [accessibilityMode, setAccessibilityMode] = useState(false);
  const [conversationId, setConversationId] = useState(null);

  const { location, requestLocation, permission } = useLocation();

  // New State for Conversations Sidebar
  const [conversations, setConversations] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

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

  // Fetch all conversations on mount
  useEffect(() => {
    fetchConversations();
  }, []);

  const fetchConversations = async () => {
    try {
      const res = await fetch("/api/conversations");
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
      }
    } catch (err) {
      console.error("Failed to fetch conversations", err);
    }
  };

  const startNewConversation = () => {
    setConversationId(null);
    setMessages(SAMPLE_MESSAGES);
    if (window.innerWidth < 768) setSidebarOpen(false);
  };

  const loadConversation = async (id) => {
    setHistoryLoading(true);
    try {
      const res = await fetch(`/api/conversations/${id}/messages`);
      if (res.ok) {
        const msgs = await res.json();
        setConversationId(id);
        if (msgs.length > 0) {
          const formatted = msgs.map((m) => ({
            role: m.role === "user" ? "user" : "model",
            content: m.content,
            is_emergency: m.risk_level === "RED",
            risk_level: m.risk_level,
          }));
          setMessages(formatted);
        } else {
          setMessages(SAMPLE_MESSAGES);
        }
      } else {
        alert("Failed to load conversation history.");
      }
    } catch (err) {
      alert("Network error while loading conversation.");
    } finally {
      setHistoryLoading(false);
      if (window.innerWidth < 768) setSidebarOpen(false);
    }
  };

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
      if (typeof navigator !== "undefined" && !navigator.onLine) {
        // --- OFFLINE MODE ---
        const {
          analyzeQueryOffline,
          getOfflineEmergencyResponse,
          getOfflineResponse,
        } = await import("../../lib/offline-triage");
        const { queueChatMessage } = await import("../../lib/db");

        const triageResult = analyzeQueryOffline(text);

        if (triageResult.isEmergency) {
          const content = getOfflineEmergencyResponse();
          setMessages((m) => [
            ...m,
            { role: "model", content, is_emergency: true },
          ]);
          if (accessibilityMode) VoiceService.speak(content, lang);
          // Queue the emergency message so it syncs later
          await queueChatMessage({
            query: text,
            conversation_id: conversationId,
            language: lang,
            roleDescription,
            is_emergency: true,
          });
        } else {
          // Queue the message to be synced later
          await queueChatMessage({
            query: text,
            conversation_id: conversationId,
            language: lang,
            roleDescription,
            is_emergency: false,
          });
          const content = getOfflineResponse(text);
          setMessages((m) => [...m, { role: "model", content }]);
          if (accessibilityMode) VoiceService.speak(content, lang);
        }
      } else {
        // --- ONLINE MODE ---
        const history = messages
          .slice(1)
          .map((m) => ({ role: m.role, content: m.content }));

        const payload = {
          query: text,
          history,
          language: lang,
          roleDescription,
          conversation_id: conversationId,
        };

        if (location) {
          payload.latitude = location.latitude;
          payload.longitude = location.longitude;
        } else if (permission === "prompt") {
          requestLocation();
        }

        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 15000);
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          signal: controller.signal,
        });
        clearTimeout(timeout);
        const data = await res.json();

        if (data.conversation_id) {
          setConversationId(data.conversation_id);
        }

        const { analyzeQueryOffline, getOfflineResponse } = await import("../../lib/offline-triage");
        const offlineResult = analyzeQueryOffline(text);
        const hasVerifiedEvidence =
          Array.isArray(data.evidence) && data.evidence.length > 0;
        const backendResponse = data.response || "";
        const isEvidenceFallback = backendResponse.toLowerCase().includes("could not find verified");
        const content =
          !res.ok ||
          data.offline ||
          isEvidenceFallback ||
          (!hasVerifiedEvidence && data.status === "success")
            ? getOfflineResponse(text)
            : backendResponse || "Sorry, I couldn't process that.";
        setMessages((m) => [
          ...m,
          {
            role: "model",
            content: content,
            evidence: data.evidence || [],
            is_emergency: data.is_emergency,
            risk_level: isEvidenceFallback ? offlineResult.riskLevel : data.risk_level,
            recommended_facilities: data.recommended_facilities || [],
          },
        ]);

        // Refresh conversations to show the new one
        if (!conversationId && data.conversation_id) {
          fetchConversations();
        }

        if (data.is_emergency) {
          VoiceService.speak(
            "Emergency detected. Please seek medical care immediately. Call 108 or go to the nearest emergency facility.",
            lang,
          );
        }
      }

      // Save to localStorage (simple history)
      const saved = JSON.parse(localStorage.getItem("medibot_chats") || "[]");
      saved.push({ date: new Date().toISOString(), symptoms: text });
      localStorage.setItem("medibot_chats", JSON.stringify(saved.slice(-20)));
    } catch {
      const {
        analyzeQueryOffline,
        getOfflineEmergencyResponse,
        getOfflineResponse,
      } = await import("../../lib/offline-triage");
      const triageResult = analyzeQueryOffline(text);
      const content = triageResult.isEmergency
        ? getOfflineEmergencyResponse()
        : getOfflineResponse(text);
      setMessages((m) => [
        ...m,
        { role: "model", content, is_emergency: triageResult.isEmergency },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const startVoice = () => {
    setListening(true);
    VoiceService.startListening(
      lang,
      (transcript, isFinal) => {
        setInput(transcript);
        if (isFinal) {
          setListening(false);
          VoiceService.stopListening();
          if (transcript.trim()) sendMessage(transcript.trim());
        }
      },
      (err) => {
        console.error(err);
        setListening(false);
        // Only alert if it's not a generic no-speech error
        if (err.error !== "no-speech") {
          alert(err.message || "Failed to start voice recognition.");
        }
      },
      () => {
        setListening(false);
      },
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
      .replace(
        /^#{1,3}\s(.+)$/gm,
        "<h4 class='font-bold text-sky-400 mt-3 mb-1'>$1</h4>",
      )
      .replace(/\n/g, "<br/>");
  };

  const quickSymptoms = [
    "Tell me a joke",
    "Explain a concept",
    "Give me advice",
    "Write some code",
    "Analyze this",
  ];

  const texts = {
    en: {
      tap: "TAP TO SPEAK",
      typing: "Or type your question...",
      ai: "Assistant",
    },
    hi: {
      tap: "बोलने के लिए टैप करें",
      typing: "या अपना सवाल टाइप करें...",
      ai: "सहायक",
    },
    mr: {
      tap: "बोलण्यासाठी टॅप करा",
      typing: "किंवा तुमचा प्रश्न टाइप करा...",
      ai: "सहाय्यक",
    },
    ta: {
      tap: "பேச தட்டவும்",
      typing: "அல்லது உங்கள் கேள்வியை தட்டச்சு செய்யவும்...",
      ai: "உதவியாளர்",
    },
    or: {
      tap: "କହିବା ପାଇଁ ଟ୍ୟାପ୍ କରନ୍ତୁ",
      typing: "କିମ୍ବା ଆପଣଙ୍କର ପ୍ରଶ୍ନ ଟାଇପ୍ କରନ୍ତୁ...",
      ai: "ସହାୟକ",
    },
  };
  const t = texts[lang] || texts.en;

  return (
    <AppLayout>
      <div
        className={`flex w-full mx-auto gap-6 ${accessibilityMode ? "max-w-4xl h-[calc(100vh-8rem)] text-lg" : "max-w-6xl h-[calc(100vh-10rem)]"}`}
      >
        {/* Conversations Sidebar (Hidden in accessibility mode for simplicity) */}
        {!accessibilityMode && (
          <div className="w-64 flex flex-col shrink-0 gap-4 hidden md:flex h-full">
            <button
              onClick={startNewConversation}
              className="glass font-bold text-sm w-full py-3 rounded-xl border border-sky-500/30 text-sky-400 hover:bg-sky-500/10 transition-all flex items-center justify-center gap-2"
            >
              <span>+</span> New Chat
            </button>

            <div className="flex-1 overflow-y-auto glass-dark rounded-xl p-2 flex flex-col gap-1">
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider px-2 py-2 mb-1">
                History
              </h3>
              {conversations.map((c) => (
                <button
                  key={c.id}
                  onClick={() => loadConversation(c.id)}
                  className={`text-left text-sm px-3 py-2.5 rounded-lg truncate transition-all ${conversationId === c.id ? "bg-sky-500/20 text-sky-300" : "text-slate-300 hover:bg-slate-800"}`}
                >
                  {c.title}
                </button>
              ))}
              {conversations.length === 0 && (
                <div className="text-xs text-slate-500 text-center mt-4">
                  No recent chats
                </div>
              )}
            </div>
          </div>
        )}

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col min-w-0 h-full">
          {/* Header */}
          <div className="flex flex-col mb-4 gap-2">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h1
                  className={`${accessibilityMode ? "text-3xl" : "text-2xl"} font-black flex items-center gap-2`}
                >
                  🤖 AI Role-based Assistant
                  {historyLoading && (
                    <span className="text-sm font-normal text-sky-400 animate-pulse">
                      (Loading...)
                    </span>
                  )}
                </h1>
                <p className="text-slate-400 text-sm">
                  Powered by Google Gemini / Groq
                </p>
              </div>
              <div className="flex flex-wrap gap-3 items-center">
                <select
                  value={lang}
                  onChange={(e) => {
                    setLang(e.target.value);
                    localStorage.setItem("medibot_lang", e.target.value);
                  }}
                  className="glass text-slate-200 text-sm py-1.5 px-3 rounded-lg bg-slate-800/80 outline-none border border-slate-700 focus:border-sky-500 cursor-pointer"
                >
                  <option value="en">English</option>
                  <option value="ta">தமிழ் (Tamil)</option>
                  <option value="hi">हिन्दी (Hindi)</option>
                  <option value="mr">मराठी (Marathi)</option>
                </select>
                <label className="flex items-center gap-2 text-slate-300 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={accessibilityMode}
                    onChange={(e) => setAccessibilityMode(e.target.checked)}
                    className="w-4 h-4 rounded bg-slate-800 border-slate-600 text-sky-500"
                  />
                  Rural Accessibility Mode
                </label>
                <button
                  onClick={() => setMessages([])}
                  className="glass px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white transition-all"
                >
                  Clear
                </button>
              </div>
            </div>
            {!accessibilityMode && (
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-slate-300">
                  Bot Role:
                </span>
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
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  className="glass px-3 py-1.5 rounded-full text-xs text-slate-300 hover:text-white hover:bg-sky-500/20 hover:border-sky-500/30 border border-transparent transition-all"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Chat messages */}
          <div
            className={`flex-1 glass-dark rounded-2xl p-4 overflow-y-auto space-y-4 mb-4 ${accessibilityMode ? "border-2 border-slate-700" : ""}`}
          >
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] ${
                    msg.role === "user"
                      ? "bg-gradient-to-r from-sky-600 to-blue-600 rounded-2xl rounded-tr-sm px-4 py-3 text-white"
                      : "glass rounded-2xl rounded-tl-sm px-4 py-3 text-slate-200"
                  } ${accessibilityMode ? "text-lg" : "text-sm"}`}
                >
                  {msg.role === "model" && (
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 bg-gradient-to-br from-sky-400 to-blue-600 rounded-full flex items-center justify-center text-xs font-bold text-white">
                          AI
                        </div>
                        <span className="text-xs text-sky-400 font-semibold">
                          {t.ai}
                        </span>
                      </div>
                      {VoiceService.isSupported() && (
                        <button
                          onClick={() => {
                            if (VoiceService.isSpeaking()) {
                              VoiceService.stopSpeaking();
                            } else {
                              VoiceService.speak(msg.content, lang);
                            }
                          }}
                          className="text-slate-400 hover:text-white flex items-center gap-1 bg-slate-800/50 px-2 py-1 rounded text-xs transition"
                          title="Read aloud"
                        >
                          🔊 Listen
                        </button>
                      )}
                    </div>
                  )}

                  <div
                    dangerouslySetInnerHTML={{
                      __html: formatMessage(msg.content),
                    }}
                    className="leading-relaxed"
                  />

                  {/* Explainable AI: Sources */}
                  {!accessibilityMode &&
                    msg.sources &&
                    msg.sources.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-slate-700/50">
                        <p className="text-xs font-semibold text-sky-400 mb-2 flex items-center gap-1">
                          Verified Medical Sources
                        </p>
                        <div className="flex flex-col gap-2">
                          {msg.sources.map((src, idx) => (
                            <div
                              key={idx}
                              className="bg-slate-800/50 rounded-lg p-2 text-[11px]"
                            >
                              <div className="flex justify-between items-center mb-1">
                                <span className="text-slate-300 font-medium truncate">
                                  {src.source}
                                </span>
                                <span
                                  className={`px-1.5 py-0.5 rounded text-[10px] ${src.relevance_score > 3 ? "bg-emerald-500/20 text-emerald-400" : "bg-amber-500/20 text-amber-400"}`}
                                >
                                  Confidence: {src.relevance_score.toFixed(1)}
                                </span>
                              </div>
                              <p className="text-slate-500 line-clamp-2 italic">
                                "{src.content}"
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                  {/* M4.2 4-Level Triage Indicators */}
                  {msg.risk_level === "RED" && (
                    <div className="mt-4 p-4 bg-red-900/60 border-2 border-red-500/80 rounded-xl">
                      <div
                        className={`flex items-center text-red-400 font-bold ${accessibilityMode ? "text-xl mb-3" : "mb-2"}`}
                      >
                        <span className="mr-2">🚨</span> CRITICAL EMERGENCY
                      </div>
                      <p
                        className={`${accessibilityMode ? "text-sm" : "text-xs"} text-red-200 mb-4`}
                      >
                        Your reported symptoms require IMMEDIATE emergency
                        medical evaluation. Do not wait.
                        <br />
                        <span className="text-red-400 font-semibold mt-2 block">
                          Status:{" "}
                          {typeof navigator !== "undefined" && !navigator.onLine
                            ? "Offline mode active"
                            : "Online connected"}
                        </span>
                      </p>
                      <div className="flex flex-col gap-3">
                        <a
                          href="tel:108"
                          className={`bg-red-600 hover:bg-red-700 text-white text-center rounded-lg font-bold transition ${accessibilityMode ? "py-4 text-lg" : "py-2 text-sm"}`}
                        >
                          Call Ambulance (108)
                        </a>

                        {/* Facility Recommendations */}
                        {msg.recommended_facilities &&
                        msg.recommended_facilities.length > 0 ? (
                          <div className="mt-2 space-y-2">
                            <p className="text-xs font-semibold text-slate-300">
                              Nearest Emergency Facilities:
                            </p>
                            {msg.recommended_facilities.map((fac, idx) => (
                              <div
                                key={idx}
                                className="bg-slate-800 p-3 rounded-lg border border-slate-700"
                              >
                                <div className="flex justify-between items-start">
                                  <div>
                                    <h5 className="text-white font-bold text-sm">
                                      {fac.name}
                                    </h5>
                                    <p className="text-xs text-slate-400">
                                      {fac.facility_type} • {fac.distance_km} km
                                      away
                                    </p>
                                    <div className="flex gap-2 mt-1">
                                      <span
                                        className={`text-[9px] px-1.5 py-0.5 rounded ${fac.emergency_available ? "bg-red-500/20 text-red-400" : "bg-slate-600 text-slate-300"}`}
                                      >
                                        ER
                                      </span>
                                      <span
                                        className={`text-[9px] px-1.5 py-0.5 rounded ${fac.verification_status === "VERIFIED" ? "bg-emerald-500/20 text-emerald-400" : fac.verification_status === "STALE" ? "bg-amber-500/20 text-amber-400" : fac.verification_status === "DEMO" ? "bg-purple-500/20 text-purple-400" : "bg-slate-500/20 text-slate-400"}`}
                                      >
                                        {fac.verification_status}
                                      </span>
                                    </div>
                                  </div>
                                  {fac.navigation && (
                                    <a
                                      href={fac.navigation.maps_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="bg-sky-600 hover:bg-sky-500 text-white text-xs px-3 py-1.5 rounded-lg font-medium transition"
                                    >
                                      Navigate
                                    </a>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <a
                            href="/facilities?emergency=true"
                            className={`bg-slate-800 hover:bg-slate-700 border border-slate-600 text-white text-center rounded-lg font-medium transition ${accessibilityMode ? "py-4 text-lg" : "py-2 text-sm"}`}
                          >
                            {location
                              ? "No nearby facilities found. Search directory"
                              : "📍 Location unavailable. Search directory manually"}
                          </a>
                        )}
                      </div>
                    </div>
                  )}

                  {msg.risk_level === "ORANGE" && (
                    <div className="mt-4 p-3 bg-orange-900/40 border-l-4 border-orange-500 rounded-r-xl">
                      <div className="flex items-center text-orange-400 font-bold mb-1">
                        <span className="mr-2">⚠️</span> URGENT EVALUATION
                        RECOMMENDED
                      </div>
                      <p className="text-xs text-orange-200 mb-3">
                        Potentially serious situation requiring prompt medical
                        evaluation. Do not delay care.
                      </p>

                      {msg.recommended_facilities &&
                      msg.recommended_facilities.length > 0 ? (
                        <div className="bg-slate-800 p-2 rounded-lg border border-slate-700 flex justify-between items-center mt-2">
                          <div>
                            <h5 className="text-white font-bold text-xs">
                              {msg.recommended_facilities[0].name}
                            </h5>
                            <p className="text-[10px] text-slate-400">
                              {msg.recommended_facilities[0].distance_km} km
                              away
                            </p>
                          </div>
                          {msg.recommended_facilities[0].navigation && (
                            <a
                              href={
                                msg.recommended_facilities[0].navigation
                                  .maps_url
                              }
                              target="_blank"
                              rel="noopener noreferrer"
                              className="bg-orange-600 hover:bg-orange-500 text-white text-[10px] px-2 py-1 rounded font-medium transition"
                            >
                              Navigate
                            </a>
                          )}
                        </div>
                      ) : (
                        <a
                          href={`/facilities?type=Hospital`}
                          className="block w-full bg-orange-600 hover:bg-orange-700 text-white text-center rounded-lg font-medium py-1.5 text-xs transition"
                        >
                          Find Nearby Hospital
                        </a>
                      )}
                    </div>
                  )}

                  {msg.risk_level === "YELLOW" && (
                    <div className="mt-4 p-3 bg-yellow-900/30 border-l-4 border-yellow-500 rounded-r-xl">
                      <div className="flex items-center text-yellow-400 font-bold mb-1">
                        <span className="mr-2">⚕️</span> ROUTINE MEDICAL CARE
                      </div>
                      <p className="text-xs text-yellow-200 mb-3">
                        Symptoms may require routine medical attention or
                        monitoring.
                      </p>

                      {msg.recommended_facilities &&
                      msg.recommended_facilities.length > 0 ? (
                        <div className="bg-slate-800 p-2 rounded-lg border border-slate-700 flex justify-between items-center mt-2">
                          <div>
                            <h5 className="text-white font-bold text-xs">
                              {msg.recommended_facilities[0].name}
                            </h5>
                            <p className="text-[10px] text-slate-400">
                              {msg.recommended_facilities[0].distance_km} km
                              away
                            </p>
                          </div>
                          {msg.recommended_facilities[0].navigation && (
                            <a
                              href={
                                msg.recommended_facilities[0].navigation
                                  .maps_url
                              }
                              target="_blank"
                              rel="noopener noreferrer"
                              className="bg-yellow-600 hover:bg-yellow-500 text-slate-900 text-[10px] px-2 py-1 rounded font-bold transition"
                            >
                              Navigate
                            </a>
                          )}
                        </div>
                      ) : (
                        <a
                          href={`/facilities?type=PHC`}
                          className="block w-full bg-yellow-600 hover:bg-yellow-700 text-slate-900 text-center rounded-lg font-bold py-1.5 text-xs transition"
                        >
                          Find Nearby Clinic (PHC)
                        </a>
                      )}
                    </div>
                  )}

                  {msg.risk_level === "GREEN" && msg.role === "model" && (
                    <div className="mt-4 p-3 bg-emerald-900/20 border-l-4 border-emerald-500 rounded-r-xl">
                      <div className="flex items-center text-emerald-400 font-bold mb-1">
                        <span className="mr-2">ℹ️</span> GENERAL HEALTH GUIDANCE
                      </div>
                      <p className="text-[10px] text-emerald-200">
                        No immediate danger detected. This is general guidance,
                        not a medical diagnosis.
                      </p>
                    </div>
                  )}

                  {msg.evidence && msg.evidence.length > 0 && (
                    <div className="mt-4 border border-slate-700 rounded-xl overflow-hidden">
                      <details className="group">
                        <summary className="flex items-center justify-between p-3 bg-slate-800 cursor-pointer hover:bg-slate-700 transition">
                          <div className="flex items-center gap-2">
                            <span className="text-sky-400">📚</span>
                            <span className="text-xs font-bold text-slate-300">
                              Sources & Evidence ({msg.evidence.length})
                            </span>
                          </div>
                          <span className="text-slate-400 group-open:rotate-180 transition-transform">
                            ▼
                          </span>
                        </summary>
                        <div className="p-3 bg-slate-900/50 flex flex-col gap-3">
                          {msg.evidence.map((ev, i) => (
                            <div
                              key={i}
                              className="text-xs border-l-2 border-sky-500 pl-3"
                            >
                              <div className="font-bold text-sky-300 mb-1">
                                {ev.title}
                              </div>
                              <div className="text-slate-400 text-[10px] mb-2 font-mono">
                                {ev.filename} (Score:{" "}
                                {(ev.relevance_score * 100).toFixed(0)}%)
                              </div>
                              <p className="text-slate-300 italic">
                                "{ev.excerpt}"
                              </p>
                            </div>
                          ))}
                        </div>
                      </details>
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
                        <div
                          key={i}
                          className="w-2 h-2 bg-sky-400 rounded-full animate-bounce"
                          style={{ animationDelay: `${i * 0.15}s` }}
                        />
                      ))}
                    </div>
                    <span className="text-xs text-slate-400">
                      Assistant is analyzing...
                    </span>
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
                <span className="font-bold text-xl tracking-wide">
                  {listening ? "LISTENING..." : t.tap}
                </span>
              </button>
              <div className="flex gap-2">
                <input
                  className="input-field flex-1 text-lg py-3"
                  placeholder={t.typing}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) =>
                    e.key === "Enter" && !e.shiftKey && sendMessage()
                  }
                />
                <button
                  onClick={() => sendMessage()}
                  disabled={loading || !input.trim()}
                  className="btn-primary px-6 font-bold disabled:opacity-50 text-lg"
                >
                  Send
                </button>
              </div>
            </div>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={listening ? stopVoice : startVoice}
                className={`glass p-3 rounded-xl transition-all ${listening ? "bg-red-500/20 border-red-500/50 text-red-400 animate-pulse" : "text-slate-400 hover:text-sky-400 hover:border-sky-500/30"} border border-transparent`}
                title={listening ? "Stop listening" : "Voice input"}
              >
                🎤
              </button>
              <input
                className="input-field flex-1"
                placeholder={listening ? "🎙️ Listening..." : t.typing}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) =>
                  e.key === "Enter" && !e.shiftKey && sendMessage()
                }
              />
              <button
                onClick={() => sendMessage()}
                disabled={loading || !input.trim()}
                className="btn-primary px-5 py-3 disabled:opacity-50"
              >
                Send
              </button>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
