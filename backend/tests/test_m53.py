import pytest
from datetime import datetime, timedelta
import os
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.db.database import get_db, Base, engine
from app.models.facility import HealthcareFacility
from app.models.user import User
from app.knowledge.facility_ingest import ingest_json, IngestStats
from app.services.facility_network import FacilityNetworkService
from app.api.deps import get_current_user, get_current_active_user, require_role
from app.main import app

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    db.query(HealthcareFacility).delete()
    db.commit()
    yield db
    db.query(HealthcareFacility).delete()
    db.commit()

def override_require_role(role: str):
    def _override():
        if role == "admin":
            return User(id=1, email="admin@test.com", role="admin")
        return User(id=2, email="user@test.com", role="user")
    return _override

def test_m53_ingest_preserves_verified_status(setup_db):
    # Insert a VERIFIED record
    setup_db.add(HealthcareFacility(
        name="Verified Clinic",
        facility_type="Clinic",
        latitude=10.0,
        longitude=10.0,
        source="MOHFW",
        source_type="GOVT",
        source_record_id="V1",
        verification_status="VERIFIED",
        verified_at=datetime.utcnow() - timedelta(days=10)
    ))
    setup_db.commit()
    
    # Ingest UNVERIFIED update
    data = [{
        "name": "Verified Clinic Updated",
        "facility_type": "Clinic",
        "latitude": "10.0",
        "longitude": "10.0",
        "source": "MOHFW",
        "source_type": "GOVT",
        "source_record_id": "V1",
        "verification_status": "UNVERIFIED"
    }]
    
    stats = ingest_json(setup_db, data)
    assert stats.skipped_verified_downgrade == 1
    assert stats.updated == 1
    
    # Check DB
    fac = setup_db.query(HealthcareFacility).filter_by(source_record_id="V1").first()
    assert fac.verification_status == "VERIFIED" # Not downgraded!
    assert fac.name == "Verified Clinic Updated"

def test_m53_stale_detection(setup_db):
    # Insert VERIFIED but very old record
    os.environ["FACILITY_STALE_DAYS"] = "180"
    fac = HealthcareFacility(
        name="Old Clinic",
        facility_type="Clinic",
        latitude=10.0,
        longitude=10.0,
        source="MOHFW",
        source_type="GOVT",
        source_record_id="ST1",
        verification_status="VERIFIED",
        verified_at=datetime.utcnow() - timedelta(days=200)
    )
    setup_db.add(fac)
    setup_db.commit()
    
    # Call service directly
    from app.services.facility_network import get_actual_verification_status
    status = get_actual_verification_status(fac)
    assert status == "STALE"

def test_m53_admin_verify_endpoints(setup_db):
    # Add unverified
    fac = HealthcareFacility(
        name="Test Clinic",
        facility_type="Clinic",
        latitude=10.0,
        longitude=10.0,
        source="MOHFW",
        source_type="GOVT",
        source_record_id="A1",
        verification_status="UNVERIFIED"
    )
    setup_db.add(fac)
    setup_db.commit()
    
    fac_id = fac.id
    
    # Verify
    # We will override get_current_user since require_role("admin") uses it internally
    app.dependency_overrides[get_current_active_user] = lambda: User(id=1, email="admin@test.com", role="admin")
    
    response = client.post(f"/api/facilities/{fac_id}/verify")
    assert response.status_code == 200
    
    setup_db.refresh(fac)
    assert fac.verification_status == "VERIFIED"
    assert fac.verified_at is not None
    
    # Mark Stale
    response = client.post(f"/api/facilities/{fac_id}/mark-stale")
    assert response.status_code == 200
    setup_db.refresh(fac)
    assert fac.verification_status == "STALE"
    
    # Reject
    response = client.post(f"/api/facilities/{fac_id}/reject")
    assert response.status_code == 200
    setup_db.refresh(fac)
    assert fac.status == "inactive"
    assert fac.verification_status == "UNVERIFIED"
    
    app.dependency_overrides.clear()

def test_m53_ranking_penalizes_demo(setup_db):
    setup_db.query(HealthcareFacility).delete()
    
    # Both identical distance and emergency capability
    f1 = HealthcareFacility(
        name="Demo Hospital", facility_type="Hospital", latitude=11.0, longitude=11.0,
        emergency_available=True, ambulance_available=True,
        verification_status="DEMO", status="active"
    )
    f2 = HealthcareFacility(
        name="Verified Hospital", facility_type="Hospital", latitude=11.0, longitude=11.0,
        emergency_available=True, ambulance_available=True,
        verification_status="VERIFIED", verified_at=datetime.utcnow(), status="active"
    )
    
    setup_db.add(f1)
    setup_db.add(f2)
    setup_db.commit()
    
    results = FacilityNetworkService.find_nearby_facilities(
        db=setup_db, latitude=11.0, longitude=11.0, radius_km=10.0
    )
    
    assert len(results) == 2
    assert results[0]["name"] == "Verified Hospital"
    assert results[1]["name"] == "Demo Hospital"


