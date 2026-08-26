/**
 * PharmacyService Foundation for M2.
 * Future Milestones will implement marketplace and delivery.
 */
export class PharmacyService {
  // ---- FUTURE IMPLEMENTATIONS ----

  static async searchMedicine(query) {
    throw new Error("Not Implemented: M2 architecture boundary. Future milestone.");
  }

  static async comparePrices(medicineId) {
    throw new Error("Not Implemented: M2 architecture boundary. Future milestone.");
  }

  static async checkAvailability(medicineId, location) {
    throw new Error("Not Implemented: M2 architecture boundary. Future milestone.");
  }

  static async findNearbyPharmacy(lat, lng) {
    throw new Error("Not Implemented: M2 architecture boundary. Future milestone.");
  }

  static async requestDelivery(orderData) {
    throw new Error("Not Implemented: M2 architecture boundary. Future milestone.");
  }
}
