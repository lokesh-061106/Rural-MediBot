/**
 * DoctorService Foundation for M2.
 * Future Milestones will implement advanced doctor matching and scheduling.
 */
export class DoctorService {
  // ---- FUTURE IMPLEMENTATIONS ----

  static async findAvailableDoctors(specialty, location) {
    throw new Error("Not Implemented: M2 architecture boundary. Future milestone.");
  }

  static async bookAppointment(doctorId, date, time) {
    throw new Error("Not Implemented: M2 architecture boundary. Future milestone.");
  }

  static async startTelemedicineSession(appointmentId) {
    // Current Jitsi implementation handles this directly in the route,
    // but future iterations will use this service boundary.
    throw new Error("Not Implemented: M2 architecture boundary. Future milestone.");
  }
}
