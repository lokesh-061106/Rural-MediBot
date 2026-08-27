import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from app.main import app
from app.db.database import get_db, Base, engine
from app.models.facility import HealthcareFacility, FacilityType
from app.models.memory import Message
from app.services.facility_network import FacilityNetworkService

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    
    # Clean up first
    db.query(HealthcareFacility).delete()
    db.query(Message).delete()
    db.commit()
    
    # Create test facilities
    f1 = HealthcareFacility(
        name="Test Hospital A (Emergency)",
        facility_type=FacilityType.DISTRICT_HOSPITAL,
        latitude=12.9716,
        longitude=77.5946, # Bangalore center
        emergency_available=True,
        ambulance_available=True,
        status="active",
        source="TEST_FIXTURE"
    )
    
    f2 = HealthcareFacility(
        name="Test Clinic B (No Emergency)",
        facility_type=FacilityType.CLINIC,
        latitude=12.9816,
        longitude=77.6046, # ~1.5km away
        emergency_available=False,
        ambulance_available=False,
        status="active",
        source="TEST_FIXTURE"
    )
    
    f3 = HealthcareFacility(
        name="Test Hospital C (Emergency - Far)",
        facility_type=FacilityType.PRIVATE_HOSPITAL,
        latitude=13.0716, # ~11km away
        longitude=77.6946,
        emergency_available=True,
        ambulance_available=True,
        status="active",
        source="TEST_FIXTURE"
    )
    
    f4 = HealthcareFacility(
        name="Inactive Hospital D",
        facility_type=FacilityType.PHC,
        latitude=12.9716,
        longitude=77.5946,
        emergency_available=True,
        status="inactive",
        source="TEST_FIXTURE"
    )
    
    db.add_all([f1, f2, f3, f4])
    db.commit()
    yield db
    
    # Teardown
    db.query(HealthcareFacility).delete()
    db.commit()

def test_haversine_calculation():
    # Distance from Bangalore to Mysore is approx 130km
    # Bangalore: 12.9716, 77.5946
    # Mysore: 12.2958, 76.6394
    from app.services.facility_network import haversine
    dist = haversine(77.5946, 12.9716, 76.6394, 12.2958)
    assert 120 < dist < 140

def test_find_nearby_facilities(setup_db):
    facilities = FacilityNetworkService.find_nearby_facilities(
        db=setup_db,
        latitude=12.9716,
        longitude=77.5946,
        radius_km=10.0
    )
    assert len(facilities) == 2
    # Should be sorted by distance, emergency, ambulance
    assert facilities[0]["name"] == "Test Hospital A (Emergency)"
    assert facilities[1]["name"] == "Test Clinic B (No Emergency)"
    
    # Inactive facility should not be returned
    assert "Inactive Hospital D" not in [f["name"] for f in facilities]

def test_find_emergency_facilities(setup_db):
    facilities = FacilityNetworkService.find_emergency_facilities(
        db=setup_db,
        latitude=12.9716,
        longitude=77.5946,
        radius_km=20.0
    )
    assert len(facilities) == 2
    assert facilities[0]["name"] == "Test Hospital A (Emergency)"
    assert facilities[1]["name"] == "Test Hospital C (Emergency - Far)"
    # Clinic B should not be here because it has no emergency
    assert "Test Clinic B (No Emergency)" not in [f["name"] for f in facilities]

def test_api_emergency_nearby():
    from app.api.deps import get_current_active_user
    app.dependency_overrides[get_current_active_user] = lambda: MagicMock(id=1, email="test@test.com")
    
    response = client.get("/api/facilities/emergency/nearby?latitude=12.9716&longitude=77.5946&radius_km=20.0&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert "distance_km" in data[0]
    assert "navigation" in data[0]
    assert data[0]["navigation"]["maps_url"].startswith("https://www.openstreetmap.org/")
    
@patch("app.agents.graph.run_medibot")
def test_chat_api_with_location(mock_run_medibot, setup_db):
    # Mock the langgraph run_medibot to return a RED emergency with recommended facilities
    mock_run_medibot.return_value = {
        "final_answer": "Please go to the hospital.",
        "is_emergency": True,
        "risk_level": "RED",
        "evidence": [],
        "recommended_facilities": FacilityNetworkService.find_emergency_facilities(
            db=setup_db, latitude=12.9716, longitude=77.5946
        )
    }
    
    response = client.post("/api/chat", json={
        "query": "I have severe chest pain",
        "language": "en",
        "latitude": 12.9716,
        "longitude": 77.5946
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["is_emergency"] is True
    assert data["risk_level"] == "RED"
    assert "recommended_facilities" in data
    assert len(data["recommended_facilities"]) == 2
    assert data["recommended_facilities"][0]["name"] == "Test Hospital A (Emergency)"

