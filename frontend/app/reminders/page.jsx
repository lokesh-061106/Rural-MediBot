"use client";
import { useState, useEffect } from "react";
import AppLayout from "@/components/AppLayout";
import { openDB } from "idb";
import { useConnectivity } from "@/hooks/useConnectivity";

export default function RemindersPage() {
  const [reminders, setReminders] = useState([]);
  const [form, setForm] = useState({ medicine_name: "", dose: "", time: "08:00", frequency: "Daily", notes: "" });
  const [showForm, setShowForm] = useState(false);
  const { isOnline } = useConnectivity();

  const initDB = async () => {
    return openDB("medibot-reminders-db", 1, {
      upgrade(db) {
        if (!db.objectStoreNames.contains("reminders")) {
          db.createObjectStore("reminders", { keyPath: "id" });
        }
      }
    });
  };

  const fetchReminders = async () => {
    try {
      if (isOnline) {
        const res = await fetch("/api/reminders");
        if (res.ok) {
          const data = await res.json();
          setReminders(data);
          
          const db = await initDB();
          const tx = db.transaction("reminders", "readwrite");
          await tx.store.clear();
          for (let r of data) {
            await tx.store.put(r);
          }
          await tx.done;
          return;
        }
      }
      // Fallback to IndexedDB
      const db = await initDB();
      const cached = await db.getAll("reminders");
      setReminders(cached);
    } catch (e) {
      console.error(e);
      // Fallback to IndexedDB
      const db = await initDB();
      const cached = await db.getAll("reminders");
      setReminders(cached);
    }
  };

  useEffect(() => {
    fetchReminders();
  }, [isOnline]);

  const addReminder = async (e) => {
    e.preventDefault();
    if (!form.medicine_name.trim()) return;
    
    try {
      if (isOnline) {
        const res = await fetch("/api/reminders", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form)
        });
        if (res.ok) {
          fetchReminders();
        }
      } else {
        // queue for offline sync would happen here via /api/sync/events
        alert("Must be online to create new reminders currently.");
      }
    } catch (e) {
      console.error(e);
    }

    setForm({ medicine_name: "", dose: "", time: "08:00", frequency: "Daily", notes: "" });
    setShowForm(false);
  };

  const toggle = async (id, currentActive) => {
    try {
      if (isOnline) {
        const res = await fetch(`/api/reminders/${id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ active: !currentActive })
        });
        if (res.ok) {
          fetchReminders();
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const remove = async (id) => {
    try {
      if (isOnline) {
        const res = await fetch(`/api/reminders/${id}`, {
          method: "DELETE"
        });
        if (res.ok) {
          fetchReminders();
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const frequencies = ["Daily", "Twice Daily", "Weekly", "As Needed"];

  return (
    <AppLayout>
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-black">💊 Medication Reminders</h1>
            <p className="text-slate-400 text-sm">{reminders.filter(r => r.active).length} active reminders</p>
          </div>
          <button onClick={() => setShowForm(!showForm)} className="btn-primary text-sm px-4 py-2">
            + Add Reminder
          </button>
        </div>
        
        {!isOnline && (
          <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 text-yellow-500 text-sm rounded-lg">
            Offline mode. Showing cached reminders. Edits are disabled until connectivity returns.
          </div>
        )}

        {/* Add Form */}
        {showForm && (
          <div className="glass-dark rounded-2xl p-6">
            <h2 className="font-bold mb-4">New Medication Reminder</h2>
            <form onSubmit={addReminder} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-slate-300 mb-1">Medication Name *</label>
                  <input required className="input-field" placeholder="e.g. Paracetamol"
                    value={form.medicine_name} onChange={(e) => setForm({ ...form, medicine_name: e.target.value })} />
                </div>
                <div>
                  <label className="block text-sm text-slate-300 mb-1">Dose</label>
                  <input className="input-field" placeholder="e.g. 500mg"
                    value={form.dose} onChange={(e) => setForm({ ...form, dose: e.target.value })} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-slate-300 mb-1">Time</label>
                  <input type="time" className="input-field" value={form.time}
                    onChange={(e) => setForm({ ...form, time: e.target.value })} />
                </div>
                <div>
                  <label className="block text-sm text-slate-300 mb-1">Frequency</label>
                  <select className="input-field" value={form.frequency}
                    onChange={(e) => setForm({ ...form, frequency: e.target.value })}>
                    {frequencies.map(f => <option key={f} value={f} className="bg-slate-900">{f}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm text-slate-300 mb-1">Notes (optional)</label>
                <input className="input-field" placeholder="Take with food..."
                  value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
              </div>
              <div className="flex gap-3">
                <button type="submit" className="btn-primary" disabled={!isOnline}>Save Reminder</button>
                <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">Cancel</button>
              </div>
            </form>
          </div>
        )}

        {/* Reminders List */}
        {reminders.length === 0 ? (
          <div className="glass-dark rounded-2xl p-12 text-center">
            <div className="text-5xl mb-4">💊</div>
            <h3 className="text-lg font-bold mb-2">No reminders yet</h3>
            <p className="text-slate-400 text-sm mb-4">Add your first medication reminder to stay on track</p>
            <button onClick={() => setShowForm(true)} className="btn-primary">Add First Reminder</button>
          </div>
        ) : (
          <div className="space-y-3">
            {reminders.map((r) => (
              <div key={r.id} className={`glass-dark rounded-2xl p-5 flex items-center justify-between border ${r.active ? "border-emerald-500/20" : "border-white/5 opacity-60"}`}>
                <div className="flex items-center gap-4">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-lg ${r.active ? "bg-emerald-500/20" : "bg-slate-800"}`}>
                    💊
                  </div>
                  <div>
                    <p className="font-bold">{r.medicine_name} {r.dose && <span className="text-slate-400 text-sm font-normal">· {r.dose}</span>}</p>
                    <p className="text-sm text-slate-400">{r.time} · {r.frequency}</p>
                    {r.notes && <p className="text-xs text-slate-500 mt-0.5">{r.notes}</p>}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => toggle(r.id, r.active)} disabled={!isOnline}
                    className={`text-xs px-3 py-1.5 rounded-lg border transition-all ${r.active ? "border-emerald-500/30 text-emerald-400 hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/30" : "border-slate-600 text-slate-400 hover:bg-emerald-500/10 hover:text-emerald-400"}`}>
                    {r.active ? "Pause" : "Resume"}
                  </button>
                  <button onClick={() => remove(r.id)} disabled={!isOnline} className="text-xs px-3 py-1.5 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 transition-all">
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
