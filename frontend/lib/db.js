import { openDB } from 'idb';

const DB_NAME = 'medibot-offline-db';
const DB_VERSION = 1;

export async function getDB() {
  if (typeof window === 'undefined') return null;
  
  return openDB(DB_NAME, DB_VERSION, {
    upgrade(db) {
      // User Profile cache
      if (!db.objectStoreNames.contains('local_profile')) {
        db.createObjectStore('local_profile', { keyPath: 'id' });
      }
      // Offline Emergency Contacts
      if (!db.objectStoreNames.contains('emergency_contacts')) {
        db.createObjectStore('emergency_contacts', { keyPath: 'id' });
      }
      // Saved Hospitals
      if (!db.objectStoreNames.contains('saved_hospitals')) {
        db.createObjectStore('saved_hospitals', { keyPath: 'id' });
      }
      // Chat Queue (Pending messages to sync)
      if (!db.objectStoreNames.contains('chat_queue')) {
        const store = db.createObjectStore('chat_queue', { keyPath: 'client_id' });
        store.createIndex('status', 'status');
      }
      // Health Events (symptoms, vitals taken offline)
      if (!db.objectStoreNames.contains('health_events')) {
        const store = db.createObjectStore('health_events', { keyPath: 'client_id' });
        store.createIndex('sync_status', 'sync_status');
      }
      // Reminders
      if (!db.objectStoreNames.contains('reminders')) {
        db.createObjectStore('reminders', { keyPath: 'id' });
      }
    }
  });
}

// ------------------------------
// Helpers for Chat Sync Queue
// ------------------------------
export async function queueChatMessage(message) {
  const db = await getDB();
  if (!db) return;
  
  const client_id = message.client_id || Date.now().toString();
  await db.put('chat_queue', {
    client_id,
    ...message,
    status: 'PENDING_SYNC',
    created_at: new Date().toISOString()
  });
  return client_id;
}

export async function getPendingChatMessages() {
  const db = await getDB();
  if (!db) return [];
  return db.getAllFromIndex('chat_queue', 'status', 'PENDING_SYNC');
}

export async function markChatMessageSynced(client_id) {
  const db = await getDB();
  if (!db) return;
  const msg = await db.get('chat_queue', client_id);
  if (msg) {
    msg.status = 'SYNCED';
    await db.put('chat_queue', msg);
  }
}

// ------------------------------
// Helpers for Profile
// ------------------------------
export async function saveLocalProfile(profileData) {
  const db = await getDB();
  if (!db) return;
  // Always use a single ID for the active user cache to keep it simple, or use their actual ID
  await db.put('local_profile', { id: 'current', ...profileData, updated_at: new Date().toISOString() });
}

export async function getLocalProfile() {
  const db = await getDB();
  if (!db) return null;
  return db.get('local_profile', 'current');
}

// ------------------------------
// Emergency / Cleanup
// ------------------------------
export async function clearLocalData() {
  const db = await getDB();
  if (!db) return;
  const tx = db.transaction(db.objectStoreNames, 'readwrite');
  for (const storeName of db.objectStoreNames) {
    tx.objectStore(storeName).clear();
  }
  await tx.done;
}
