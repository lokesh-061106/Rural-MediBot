import { getDB } from '../db';

/**
 * HospitalService Foundation for M3.
 * Handles online API calls and offline IndexedDB fallback.
 */
export class HospitalService {
  static async getSavedHospitals() {
    const db = await getDB();
    if (!db) return [];
    return db.getAll('saved_hospitals');
  }

  static async saveHospital(hospitalData) {
    const db = await getDB();
    if (!db) return;
    await db.put('saved_hospitals', hospitalData);
  }
  
  static async unSaveHospital(hospitalId) {
    const db = await getDB();
    if (!db) return;
    await db.delete('saved_hospitals', hospitalId);
  }
  
  static async isHospitalSaved(hospitalId) {
    const db = await getDB();
    if (!db) return false;
    const hospital = await db.get('saved_hospitals', hospitalId);
    return !!hospital;
  }

  // --- API CALLS WITH OFFLINE CACHING ---
  
  static async findNearbyHospitals(lat, lng, radius_km = 20, type = null, emergency = null) {
    try {
      if (!navigator.onLine) throw new Error("Offline");
      
      let url = `/api/facilities/nearby?latitude=${lat}&longitude=${lng}&radius_km=${radius_km}`;
      if (type) url += `&facility_type=${type}`;
      if (emergency !== null) url += `&emergency=${emergency}`;
      
      const res = await fetch(url);
      if (!res.ok) throw new Error("API Error");
      
      const data = await res.json();
      
      // Cache the results for offline
      const db = await getDB();
      if (db) {
        const tx = db.transaction('facility_cache', 'readwrite');
        data.forEach(facility => tx.store.put(facility));
        await tx.done;
      }
      return { data, source: 'online' };
    } catch (e) {
      // Fallback to IndexedDB
      const db = await getDB();
      if (!db) return { data: [], source: 'offline' };
      
      const allCached = await db.getAll('facility_cache');
      let filtered = allCached.filter(f => {
        // basic boundary box filter for offline
        const latDiff = Math.abs(f.latitude - lat);
        const lonDiff = Math.abs(f.longitude - lng);
        if (latDiff > 0.5 || lonDiff > 0.5) return false; // Roughly 50km box
        
        if (type && f.facility_type !== type) return false;
        if (emergency !== null && f.emergency_available !== emergency) return false;
        return true;
      });
      return { data: filtered, source: 'offline' };
    }
  }

  static async getHospitalDetails(hospitalId) {
    try {
      if (!navigator.onLine) throw new Error("Offline");
      const res = await fetch(`/api/facilities/${hospitalId}`);
      if (!res.ok) throw new Error("API Error");
      const data = await res.json();
      
      // Cache
      const db = await getDB();
      if (db) await db.put('facility_cache', data);
      
      return { data, source: 'online' };
    } catch (e) {
      const db = await getDB();
      if (!db) return null;
      const data = await db.get('facility_cache', parseInt(hospitalId));
      if (!data) {
          // Check saved hospitals too
          const saved = await db.get('saved_hospitals', parseInt(hospitalId));
          if (saved) return { data: saved, source: 'offline' };
      }
      return data ? { data, source: 'offline' } : null;
    }
  }

  static getDirectionsLink(lat, lng) {
    // Universal link that works on mobile maps app or desktop browser
    return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
  }

  static async getEmergencyHospitals(lat, lng) {
    return this.findNearbyHospitals(lat, lng, 50, null, true);
  }
}
