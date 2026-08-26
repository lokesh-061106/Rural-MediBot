"use client";

import { useConnectivity } from '../hooks/useConnectivity';
import { useEffect, useState } from 'react';

export default function ConnectivityBadge({ syncStatus = 'IDLE' }) {
  const { isOnline } = useConnectivity();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  if (!isOnline) {
    return (
      <div className="flex items-center space-x-2 bg-red-900/50 text-red-200 px-3 py-1 rounded-full text-xs font-medium border border-red-800">
        <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
        <span>Offline Mode</span>
      </div>
    );
  }

  if (syncStatus === 'SYNCING') {
    return (
      <div className="flex items-center space-x-2 bg-yellow-900/50 text-yellow-200 px-3 py-1 rounded-full text-xs font-medium border border-yellow-800">
        <svg className="animate-spin w-3 h-3 text-yellow-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span>Synchronizing...</span>
      </div>
    );
  }

  // When online and not actively syncing, we show a subtle connected indicator
  return (
    <div className="flex items-center space-x-2 bg-emerald-900/30 text-emerald-300 px-3 py-1 rounded-full text-xs font-medium border border-emerald-800/50">
      <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
      <span>Connected</span>
    </div>
  );
}
