"use client";

import { useState, useEffect } from 'react';

export function useConnectivity() {
  const [isOnline, setIsOnline] = useState(true); // Default to true, update on mount

  useEffect(() => {
    // Set initial state
    setIsOnline(navigator.onLine);

    const handleOnline = () => {
      setIsOnline(true);
      // Attempt sync when connectivity returns
      import('../lib/syncEngine').then(({ processSyncQueue }) => {
        processSyncQueue();
      });
    };

    const handleOffline = () => {
      setIsOnline(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return { isOnline };
}
