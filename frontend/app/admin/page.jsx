"use client";
import { useState, useEffect } from "react";
import AppLayout from "@/components/AppLayout";

export default function AdminDashboard() {
  const [data, setData] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch("/api/admin/overview").then(res => res.json()),
      fetch("/api/admin/audit-logs?limit=5").then(res => res.json())
    ]).then(([overview, auditLogs]) => {
      setData(overview);
      setLogs(auditLogs || []);
      setLoading(false);
    }).catch(err => {
      console.error(err);
      setLoading(false);
    });
  }, []);

  if (loading) return <AppLayout><div className="p-8">Loading admin data...</div></AppLayout>;

  const stats = [
    { label: "Total Users", value: data?.stats?.total_users || 0, color: "from-sky-500/20 to-blue-500/20 text-sky-400 border-sky-500/30" },
    { label: "Active Doctors", value: data?.stats?.active_doctors || 0, color: "from-emerald-500/20 to-green-500/20 text-emerald-400 border-emerald-500/30" },
    { label: "AI Consultations", value: data?.stats?.ai_consultations || 0, color: "from-purple-500/20 to-violet-500/20 text-purple-400 border-purple-500/30" },
    { label: "Total Facilities", value: data?.stats?.total_facilities || 0, color: "from-rose-500/20 to-pink-500/20 text-rose-400 border-rose-500/30" },
  ];

  return (
    <AppLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-black">⚙️ Admin Control Panel</h1>
          <p className="text-slate-400 text-sm">System analytics and user management.</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {stats.map((s) => (
            <div key={s.label} className={`glass-dark rounded-2xl p-5 border bg-gradient-to-br ${s.color}`}>
              <div className="text-3xl font-black mb-1">{s.value}</div>
              <div className="text-slate-400 text-xs uppercase tracking-wider font-semibold">{s.label}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="glass-dark rounded-2xl p-6">
            <h2 className="font-bold mb-4">System Status</h2>
            <div className="space-y-4">
              {(data?.system_status || []).map(s => (
                <div key={s.name} className="flex justify-between items-center border-b border-white/5 pb-2 last:border-0 last:pb-0">
                  <span className="text-slate-300 text-sm">{s.name}</span>
                  <span className={`text-xs font-bold ${s.color}`}>● {s.status}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-dark rounded-2xl p-6">
            <h2 className="font-bold mb-4">Recent Audit Events</h2>
            <div className="space-y-3">
              {logs.length === 0 && <p className="text-sm text-slate-400">No events found.</p>}
              {logs.map(log => (
                <div key={log.id} className="p-3 bg-white/5 border border-white/10 rounded-xl flex flex-col gap-1">
                  <div className="flex justify-between">
                    <span className="text-sky-400 text-sm font-semibold">{log.action}</span>
                    <span className="text-xs text-slate-500">{new Date(log.timestamp).toLocaleString()}</span>
                  </div>
                  <p className="text-xs text-slate-400">By: {log.user_email} | Resource: {log.resource} ({log.resource_id})</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
