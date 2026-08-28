import { getDB } from "../db";

const OFFLINE_FACILITIES = [
  {
    id: "offline-pune-general",
    name: "Pune General Hospital",
    facility_type: "District Hospital",
    ownership: "Public",
    address: "123 Main St, Pune, Maharashtra 411001",
    latitude: 18.5204,
    longitude: 73.8567,
    phone: "020-12345678",
    emergency_available: true,
    status: "active",
    source: "OFFLINE_DIRECTORY",
  },
  {
    id: "offline-shirur-phc",
    name: "Shirur Primary Health Centre",
    facility_type: "PHC",
    ownership: "Public",
    address: "PHC Road, Shirur, Pune, Maharashtra 412210",
    latitude: 18.8291,
    longitude: 74.3725,
    phone: "02138-123456",
    emergency_available: false,
    status: "active",
    source: "OFFLINE_DIRECTORY",
  },
  {
    id: "offline-khed-chc",
    name: "Khed Community Health Centre",
    facility_type: "CHC",
    ownership: "Public",
    address: "CHC Road, Khed, Pune, Maharashtra 410505",
    latitude: 18.8475,
    longitude: 73.9038,
    phone: "02135-123456",
    emergency_available: true,
    status: "active",
    source: "OFFLINE_DIRECTORY",
  },
];

function filterOfflineFacilities(type, emergency) {
  return OFFLINE_FACILITIES.filter(
    (facility) =>
      (!type || facility.facility_type === type) &&
      (emergency === null || facility.emergency_available === emergency),
  );
}

async function fetchWithTimeout(url, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
}

/**
 * HospitalService Foundation for M3.
 * Handles online API calls and offline IndexedDB fallback.
 */
export class HospitalService {
  static async getSavedHospitals() {
    const db = await getDB();
    if (!db) return [];
    return db.getAll("saved_hospitals");
  }

  static async saveHospital(hospitalData) {
    const db = await getDB();
    if (!db) return;
    await db.put("saved_hospitals", hospitalData);
  }

  static async unSaveHospital(hospitalId) {
    const db = await getDB();
    if (!db) return;
    await db.delete("saved_hospitals", hospitalId);
  }

  static async isHospitalSaved(hospitalId) {
    const db = await getDB();
    if (!db) return false;
    const hospital = await db.get("saved_hospitals", hospitalId);
    return !!hospital;
  }

  // --- API CALLS WITH OFFLINE CACHING ---

  static async findNearbyHospitals(
    lat,
    lng,
    radius_km = 20,
    type = null,
    emergency = null,
  ) {
    try {
      if (!navigator.onLine) throw new Error("Offline");

      let url = `/api/facilities/nearby?latitude=${lat}&longitude=${lng}&radius_km=${radius_km}`;
      if (type) url += `&facility_type=${type}`;
      if (emergency !== null) url += `&emergency=${emergency}`;

      const res = await fetchWithTimeout(url);
      if (!res.ok) throw new Error("API Error");

      const data = await res.json();

      // Cache the results for offline
      const db = await getDB();
      if (db) {
        const tx = db.transaction("facility_cache", "readwrite");
        data.forEach((facility) => tx.store.put(facility));
        await tx.done;
      }
      return { data, source: "online" };
    } catch (e) {
      // Fallback to IndexedDB
      const db = await getDB();
      if (!db)
        return {
          data: filterOfflineFacilities(type, emergency),
          source: "offline",
        };

      const allCached = await db.getAll("facility_cache");
      if (allCached.length === 0) {
        return {
          data: filterOfflineFacilities(type, emergency),
          source: "offline",
        };
      }
      let filtered = allCached.filter((f) => {
        // basic boundary box filter for offline
        const latDiff = Math.abs(f.latitude - lat);
        const lonDiff = Math.abs(f.longitude - lng);
        if (latDiff > 0.5 || lonDiff > 0.5) return false; // Roughly 50km box

        if (type && f.facility_type !== type) return false;
        if (emergency !== null && f.emergency_available !== emergency)
          return false;
        return true;
      });
      return { data: filtered, source: "offline" };
    }
  }

  static async findAllHospitals(type = null, emergency = null) {
    try {
      if (!navigator.onLine) throw new Error("Offline");

      let url = "/api/facilities?limit=500";
      if (type) url += `&facility_type=${encodeURIComponent(type)}`;
      if (emergency !== null) url += `&emergency=${emergency}`;

      const res = await fetchWithTimeout(url);
      if (!res.ok) throw new Error("API Error");

      const data = await res.json();
      const db = await getDB();
      if (db) {
        const tx = db.transaction("facility_cache", "readwrite");
        data.forEach((facility) => tx.store.put(facility));
        await tx.done;
      }
      return { data, source: "online" };
    } catch (e) {
      const db = await getDB();
      if (!db)
        return {
          data: filterOfflineFacilities(type, emergency),
          source: "offline",
        };
      const allCached = await db.getAll("facility_cache");
      const filtered = allCached.filter(
        (f) =>
          (!type || f.facility_type === type) &&
          (emergency === null || f.emergency_available === emergency),
      );
      return {
        data: filtered.length
          ? filtered
          : filterOfflineFacilities(type, emergency),
        source: "offline",
      };
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
      if (db) await db.put("facility_cache", data);

      return { data, source: "online" };
    } catch (e) {
      const db = await getDB();
      const offlineFacility = OFFLINE_FACILITIES.find(
        (facility) => String(facility.id) === String(hospitalId),
      );
      if (!db)
        return offlineFacility
          ? { data: offlineFacility, source: "offline" }
          : null;
      const data = await db.get("facility_cache", hospitalId);
      if (!data) {
        // Check saved hospitals too
        const saved = await db.get("saved_hospitals", hospitalId);
        if (saved) return { data: saved, source: "offline" };
      }
      return data
        ? { data, source: "offline" }
        : offlineFacility
          ? { data: offlineFacility, source: "offline" }
          : null;
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
