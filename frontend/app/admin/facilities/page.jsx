"use client";
import { useState, useEffect } from "react";
import AppLayout from "@/components/AppLayout";
import Link from "next/link";
import { useConnectivity } from "@/hooks/useConnectivity";

export default function AdminFacilities() {
  const [facilities, setFacilities] = useState([]);
  const [loading, setLoading] = useState(true);
  const { isOnline } = useConnectivity();
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      if (!isOnline) {
        setError("Admin panel requires internet connection.");
        setLoading(false);
        return;
      }
      try {
        const res = await fetch(`/api/facilities?limit=500`);
        if (!res.ok) throw new Error("Failed to load");
        const data = await res.json();
        setFacilities(data);
      } catch (e) {
        setError("Error loading facilities.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [isOnline]);

  return (
    <AppLayout>
      <div className="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
        <div className="sm:flex sm:items-center sm:justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">Facility Management</h1>
            <p className="mt-2 text-sm text-slate-400">Manage healthcare facilities, types, and verification status.</p>
          </div>
          <div className="mt-4 sm:mt-0">
            <button className="bg-sky-600 hover:bg-sky-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition">
              + Add Facility
            </button>
          </div>
        </div>

        {error ? (
          <div className="bg-red-900/40 border border-red-500/50 p-4 rounded-xl text-red-200">
            {error}
          </div>
        ) : loading ? (
          <div className="text-slate-400">Loading facilities...</div>
        ) : (
          <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-800">
                <thead className="bg-slate-900/50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Name</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Type</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Location</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Emergency</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 bg-slate-900">
                  {facilities.map((f) => (
                    <tr key={f.id} className="hover:bg-slate-800/50 transition">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">{f.name}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">{f.facility_type}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">{f.district}, {f.state}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {f.emergency_available ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-900/40 text-red-400">Yes</span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-800 text-slate-400">No</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${f.status === 'active' ? 'bg-emerald-900/40 text-emerald-400' : 'bg-slate-800 text-slate-400'}`}>
                          {f.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <Link href={`/facilities/${f.id}`} className="text-sky-400 hover:text-sky-300 mr-4">View</Link>
                        <button className="text-slate-400 hover:text-white">Edit</button>
                      </td>
                    </tr>
                  ))}
                  {facilities.length === 0 && (
                    <tr>
                      <td colSpan="6" className="px-6 py-8 text-center text-slate-500">No facilities found.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
