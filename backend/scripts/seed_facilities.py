import os
import sys
from datetime import datetime
import json

# Ensure we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine
from app.models.facility import HealthcareFacility, FacilityType

def validate_facility(fac):
    if not fac.get("name"):
        return False, "Missing name"
    if not fac.get("facility_type") or fac["facility_type"] not in [e.value for e in FacilityType]:
        return False, "Invalid facility type"
    if fac.get("latitude") is not None:
        if not (-90 <= fac["latitude"] <= 90):
            return False, "Invalid latitude"
    if fac.get("longitude") is not None:
        if not (-180 <= fac["longitude"] <= 180):
            return False, "Invalid longitude"
    return True, ""

def seed_facilities():
    # Sample DEMO data
    demo_facilities = [
        {
            "name": "Pune General Hospital",
            "facility_type": FacilityType.DISTRICT_HOSPITAL.value,
            "ownership": "Public",
            "address": "123 Main St",
            "district": "Pune",
            "state": "Maharashtra",
            "pincode": "411001",
            "latitude": 18.5204,
            "longitude": 73.8567,
            "phone": "020-12345678",
            "emergency_available": True,
            "source": "DEMO",
            "verification_status": "VERIFIED",
            "status": "active"
        },
        {
            "name": "Shirur Primary Health Centre",
            "facility_type": FacilityType.PHC.value,
            "ownership": "Public",
            "address": "PHC Road",
            "village": "Shirur",
            "district": "Pune",
            "state": "Maharashtra",
            "pincode": "412210",
            "latitude": 18.8291,
            "longitude": 74.3725,
            "phone": "02138-123456",
            "emergency_available": False,
            "source": "DEMO",
            "verification_status": "VERIFIED",
            "status": "active"
        },
        {
            "name": "Khed Community Health Centre",
            "facility_type": FacilityType.CHC.value,
            "ownership": "Public",
            "address": "CHC Road",
            "village": "Khed",
            "district": "Pune",
            "state": "Maharashtra",
            "pincode": "410505",
            "latitude": 18.8475,
            "longitude": 73.9038,
            "phone": "02135-123456",
            "emergency_available": True,
            "source": "DEMO",
            "verification_status": "VERIFIED",
            "status": "active"
        }
    ]

    db = SessionLocal()
    try:
        added = 0
        skipped = 0
        for fac_data in demo_facilities:
            is_valid, err = validate_facility(fac_data)
            if not is_valid:
                print(f"Skipping {fac_data.get('name')}: {err}")
                continue
                
            # Idempotency check: by name and district
            existing = db.query(HealthcareFacility).filter(
                HealthcareFacility.name == fac_data["name"],
                HealthcareFacility.district == fac_data["district"]
            ).first()
            
            if existing:
                # Update existing
                for key, value in fac_data.items():
                    setattr(existing, key, value)
                existing.last_updated = datetime.utcnow()
                existing.verified_at = datetime.utcnow()
                print(f"Updated existing facility: {fac_data['name']}")
                skipped += 1
            else:
                # Create new
                new_fac = HealthcareFacility(**fac_data)
                new_fac.verified_at = datetime.utcnow()
                db.add(new_fac)
                print(f"Added new facility: {fac_data['name']}")
                added += 1
                
        db.commit()
        print(f"\nSeed completed! Added: {added}, Updated/Skipped: {skipped}")
    except Exception as e:
        db.rollback()
        print(f"Error seeding facilities: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_facilities()
