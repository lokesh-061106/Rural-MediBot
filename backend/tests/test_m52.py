import pytest
from sqlalchemy.orm import Session
from app.db.database import get_db, Base, engine
from app.models.facility import HealthcareFacility
from app.knowledge.facility_ingest import ingest_json, IngestStats
from app.services.facility_network import FacilityNetworkService

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    db.query(HealthcareFacility).delete()
    db.commit()
    yield db
    db.query(HealthcareFacility).delete()
    db.commit()

def test_ingest_json_valid(setup_db):
    data = [
        {
            "name": "Govt Hospital A",
            "facility_type": "Hospital",
            "latitude": "12.0",
            "longitude": "77.0",
            "source": "MOHFW",
            "source_type": "GOVT",
            "source_record_id": "G100",
            "emergency_available": "true",
            "verification_status": "VERIFIED"
        },
        {
            "name": "PHC B",
            "facility_type": "PHC",
            "latitude": "12.1",
            "longitude": "77.1",
            "source": "MOHFW",
            "source_type": "GOVT",
            "source_record_id": "G101",
            "emergency_available": "false",
            "verification_status": "VERIFIED"
        }
    ]
    stats = ingest_json(setup_db, data)
    assert stats.total_records == 2
    assert stats.accepted == 2
    assert stats.inserted == 2
    
    # Check DB
    fac = setup_db.query(HealthcareFacility).filter_by(source_record_id="G100").first()
    assert fac is not None
    assert fac.verification_status == "VERIFIED"
    assert fac.emergency_available is True

def test_ingest_invalid_coordinates(setup_db):
    data = [
        {
            "name": "Bad GPS",
            "facility_type": "PHC",
            "latitude": "900.0", # Invalid
            "longitude": "77.0",
            "source": "TEST",
            "source_type": "API",
            "source_record_id": "T1"
        }
    ]
    stats = ingest_json(setup_db, data)
    assert stats.total_records == 1
    assert stats.rejected == 1
    assert stats.invalid_coordinates == 1
    assert stats.inserted == 0

def test_ingest_missing_required_fields(setup_db):
    data = [
        {
            "name": "", # Missing name
            "latitude": "12.0",
            "longitude": "77.0",
            "source": "TEST",
            "source_type": "API",
            "source_record_id": "T2"
        },
        {
            "name": "No Source",
            "latitude": "12.0",
            "longitude": "77.0",
            "source_record_id": "T3"
        }
    ]
    stats = ingest_json(setup_db, data)
    assert stats.rejected == 2

def test_ingest_idempotent_and_update(setup_db):
    data = [
        {
            "name": "Govt Hospital A - Updated", # Changed name
            "facility_type": "Hospital",
            "latitude": "12.0",
            "longitude": "77.0",
            "source": "MOHFW",
            "source_type": "GOVT",
            "source_record_id": "G100", # Same ID
            "emergency_available": "true",
            "verification_status": "VERIFIED"
        }
    ]
    stats = ingest_json(setup_db, data)
    assert stats.updated == 1
    assert stats.inserted == 0
    assert stats.duplicates == 1
    
    fac = setup_db.query(HealthcareFacility).filter_by(source_record_id="G100").first()
    assert fac.name == "Govt Hospital A - Updated"

def test_m51_ranking_respects_status(setup_db):
    facilities = FacilityNetworkService.find_nearby_facilities(
        db=setup_db,
        latitude=12.0,
        longitude=77.0,
        radius_km=20.0
    )
    assert len(facilities) == 2
    # The G100 is emergency_available=True, so it should rank higher
    assert facilities[0]["facility_id"] == str(setup_db.query(HealthcareFacility).filter_by(source_record_id="G100").first().id)
    assert facilities[0]["verification_status"] == "VERIFIED"

