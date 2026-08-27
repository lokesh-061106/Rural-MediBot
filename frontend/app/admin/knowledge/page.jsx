"use client";
import { useState, useEffect } from "react";
import AppLayout from "@/components/AppLayout";
import { useRouter } from "next/navigation";

export default function AdminKnowledge() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reviewDoc, setReviewDoc] = useState(null);
  
  // 10 checklist items
  const initialChecks = Array(10).fill(false);
  const [checks, setChecks] = useState(initialChecks);
  
  const router = useRouter();

  const loadData = () => {
    fetch("/api/admin/knowledge/readiness")
      .then(res => res.json())
      .then(d => {
        setData(d);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, []);

  const checklistItems = [
    "I inspected the actual document.",
    "The issuing authority is identifiable.",
    "The publisher is identifiable.",
    "The source URL is verified.",
    "Publication/version information is established.",
    "The document appears to be an official health/clinical/public-health document.",
    "The document is not DEMO.",
    "The document is not corrupted.",
    "The document is sufficiently current according to DATA_READINESS.md.",
    "The document is appropriate for the Medibot knowledge base."
  ];

  const handleToggleCheck = (index) => {
    const newChecks = [...checks];
    newChecks[index] = !newChecks[index];
    setChecks(newChecks);
  };

  const allChecked = checks.every(c => c);

  const openReviewModal = (doc) => {
    setReviewDoc(doc);
    setChecks(initialChecks);
  };

  const handleAction = async (docId, action, payload = {}) => {
    try {
      const res = await fetch(`/api/admin/knowledge/documents/${docId}/${action}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: Object.keys(payload).length > 0 ? JSON.stringify(payload) : undefined
      });
      if (res.ok) {
        alert(`Document ${action}ed successfully`);
        setReviewDoc(null);
        loadData();
      } else {
        const error = await res.json();
        alert(`Failed: ${error.detail || 'Unknown error'}`);
      }
    } catch (e) {
      alert("Network error");
    }
  };

  if (loading) return <AppLayout><div className="p-8">Loading...</div></AppLayout>;

  const docs = data?.documents || [];

  return (
    <AppLayout>
      <div className="space-y-6 relative">
        <div>
          <h1 className="text-2xl font-black">📚 Knowledge Base Admin</h1>
          <p className="text-slate-400 text-sm">Review, verify, and activate authoritative medical documents.</p>
        </div>

        <div className="glass-dark rounded-2xl p-6 mb-6">
          <h2 className="font-bold mb-4 text-rose-400">⚠️ Strict Warning</h2>
          <p className="text-sm text-slate-300">
            Verification means a human administrator has reviewed the actual document and approved its authority and provenance for clinical use. Do not verify based solely on filename, formatting, or AI-generated claims.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4">
          {docs.length === 0 && <p className="text-slate-400">No documents found.</p>}
          {docs.map(doc => (
            <div key={doc.id} className="glass-dark border border-white/10 rounded-2xl p-5 space-y-3 flex flex-col md:flex-row justify-between items-start md:items-center">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-lg">{doc.title || doc.filename}</h3>
                  <span className={`text-xs px-2 py-1 rounded-full font-bold ${doc.status === 'ACTIVE' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-500/20 text-slate-400'}`}>
                    {doc.status}
                  </span>
                  <span className={`text-xs px-2 py-1 rounded-full font-bold ${doc.verification_status === 'VERIFIED' ? 'bg-sky-500/20 text-sky-400' : 'bg-rose-500/20 text-rose-400'}`}>
                    {doc.verification_status}
                  </span>
                  {doc.is_authoritative && <span className="text-xs px-2 py-1 rounded-full font-bold bg-amber-500/20 text-amber-400">Authoritative</span>}
                </div>
                <div className="text-xs text-slate-400 grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1">
                  <div><span className="font-semibold text-slate-300">ID:</span> {doc.id}</div>
                  <div><span className="font-semibold text-slate-300">File:</span> {doc.filename}</div>
                  <div><span className="font-semibold text-slate-300">Publisher:</span> {doc.publisher || "N/A"}</div>
                  <div><span className="font-semibold text-slate-300">Source URL:</span> {doc.source_url || "N/A"}</div>
                  <div><span className="font-semibold text-slate-300">Pub Date:</span> {doc.publication_date || "N/A"}</div>
                  <div><span className="font-semibold text-slate-300">Hash:</span> {doc.content_hash.substring(0, 8)}...</div>
                  <div><span className="font-semibold text-slate-300">Version:</span> {doc.version}</div>
                  <div><span className="font-semibold text-slate-300">Pages/Chunks:</span> {doc.chunk_count}</div>
                  <div><span className="font-semibold text-slate-300">Created:</span> {new Date(doc.created_at).toLocaleString()}</div>
                  <div><span className="font-semibold text-slate-300">Verified:</span> {doc.verified_at ? new Date(doc.verified_at).toLocaleString() : "Never"}</div>
                </div>
              </div>

              <div className="flex flex-col gap-2 min-w-[120px]">
                {doc.status !== 'ACTIVE' && doc.status !== 'DEPRECATED' && doc.verification_status !== 'VERIFIED' && (
                  <button 
                    onClick={() => openReviewModal(doc)}
                    className="px-3 py-1.5 bg-sky-600 hover:bg-sky-500 rounded text-sm font-bold transition-colors text-white"
                  >
                    Review
                  </button>
                )}
                {doc.verification_status === 'VERIFIED' && doc.status !== 'ACTIVE' && (
                  <button 
                    onClick={() => handleAction(doc.id, 'activate')}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded text-sm font-bold transition-colors text-white"
                  >
                    Activate
                  </button>
                )}
                {doc.status !== 'REJECTED' && (
                  <button 
                    onClick={() => handleAction(doc.id, 'reject')}
                    className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 rounded text-sm font-bold transition-colors text-white"
                  >
                    Reject
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Modal */}
        {reviewDoc && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="bg-slate-900 border border-slate-700 p-6 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl">
              <h2 className="text-xl font-bold mb-4">Review Document: {reviewDoc.filename}</h2>
              <div className="mb-6 bg-slate-800/50 p-4 rounded-xl text-sm space-y-2 border border-slate-700">
                  <div><strong>Title:</strong> {reviewDoc.title || 'N/A'}</div>
                  <div><strong>Publisher:</strong> {reviewDoc.publisher || 'N/A'}</div>
                  <div><strong>Issuing Authority:</strong> {reviewDoc.issuing_authority || reviewDoc.publisher || 'N/A'}</div>
                  <div><strong>Source URL:</strong> {reviewDoc.source_url || 'N/A'}</div>
                  <div><strong>Publication Date:</strong> {reviewDoc.publication_date || 'N/A'}</div>
                  <div><strong>Version:</strong> {reviewDoc.version || 'N/A'}</div>
                  <div><strong>Page Count:</strong> {reviewDoc.chunk_count || 'N/A'}</div>
                  <div><strong>Hash:</strong> {reviewDoc.content_hash || 'N/A'}</div>
                  <div><strong>Status:</strong> {reviewDoc.status}</div>
              </div>
              <div className="space-y-3 mb-6">
                <p className="font-bold text-sky-400">Human Review Checklist</p>
                {checklistItems.map((item, idx) => (
                  <label key={idx} className="flex items-start gap-3 cursor-pointer">
                    <input type="checkbox" checked={checks[idx]} onChange={() => handleToggleCheck(idx)} className="mt-1 w-4 h-4 rounded border-slate-600 text-sky-500 focus:ring-sky-500 focus:ring-offset-slate-900 bg-slate-800" />
                    <span className="text-sm text-slate-300 select-none">{item}</span>
                  </label>
                ))}
              </div>
              
              <div className="flex gap-4 justify-end">
                <button onClick={() => setReviewDoc(null)} className="px-4 py-2 rounded font-bold text-slate-400 hover:bg-slate-800">
                  Cancel
                </button>
                <button 
                  onClick={() => handleAction(reviewDoc.id, 'verify', { checklist_confirmed: true })}
                  disabled={!allChecked}
                  className={`px-4 py-2 rounded font-bold transition-colors ${allChecked ? 'bg-sky-600 hover:bg-sky-500 text-white' : 'bg-slate-700 text-slate-500 cursor-not-allowed'}`}
                >
                  Verify Document
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </AppLayout>
  );
}
