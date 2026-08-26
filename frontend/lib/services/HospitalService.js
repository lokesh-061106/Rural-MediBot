import { getDB } from '../db';

/**
 * HospitalService Foundation for M2.
 * Future Milestones will implement OpenStreetMap / Government hospital integrations.
 */
export class HospitalService {
  /**
   * Retrieves saved hospitals from local IndexedDB offline storage.
   */
  static async getSavedHospitals() {
    const db = await getDB();
    if (!db) return [];
    return db.getAll('saved_hospitals');
  }

  /**
   * Saves a hospital to local offline storage.
   */
  static async saveHospital(hospitalData) {
    const db = await getDB();
    if (!db) return;
    await db.put('saved_hospitals', hospitalData);
  }

  // ---- FUTURE IMPLEMENTATIONS ----

  static async findNearbyHospitals(lat, lng) {
    throw new Error("Not Implemented: M2 architecture boundary. Future milestone.");
  }

  static async getHospitalDetails(hospitalId) {
    throw new Error("Not Implemented: M2 architecture boundary. Future milestone.");
  }

  static async getDirections(from, to) {
    throw new Error("Not Implemented: M2 architecture boundary. Future milestone.");
  }

  static async getEmergencyHospitals() {
    throw new Error("Not Implemented: M2 architecture boundary. Future milestone.");
  }
}
