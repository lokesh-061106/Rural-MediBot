import { getPendingChatMessages, markChatMessageSynced } from './db';

// This function processes all offline items when the user comes back online
export async function processSyncQueue() {
  if (typeof window === 'undefined' || !navigator.onLine) return;

  const tokenMatch = document.cookie.match(/(^| )medibot_token=([^;]+)/);
  if (!tokenMatch) return; // User is not logged in

  try {
    // 1. Sync Chat Messages
    const pendingChats = await getPendingChatMessages();
    if (pendingChats.length > 0) {
      console.log(`[Sync] Found ${pendingChats.length} pending chat messages.`);
      
      const payload = {
        events: pendingChats.map(c => ({
          client_id: c.client_id,
          event_type: 'chat_query',
          payload: { query: c.query, thread_id: c.thread_id },
          created_at: c.created_at
        }))
      };

      const res = await fetch('/api/sync/events', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        // Mark synced items locally
        for (const cid of data.synced_client_ids) {
          await markChatMessageSynced(cid);
        }
        console.log(`[Sync] Successfully synced ${data.synced_client_ids.length} messages.`);
      }
    }
  } catch (error) {
    console.error("[Sync] Sync failed. Will retry later.", error);
  }
}

// In a real PWA, you would also use the Background Sync API (sync event in service worker).
// For M2, we use a simple active poll or event listener in the client.
