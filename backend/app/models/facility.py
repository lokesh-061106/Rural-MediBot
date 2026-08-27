from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from app.db.database import Base

class FacilityType(str, enum.Enum):
    PHC = "PHC"
    CHC = "CHC"
    DISTRICT_HOSPITAL = "District Hospital"
    GOVERNMENT_HOSPITAL = "Government Hospital"
    SUB_CENTRE = "Sub-Centre"
    PRIVATE_HOSPITAL = "Private Hospital"
    CLINIC = "Clinic"
    PHARMACY = "Pharmacy"
    DIAGNOSTIC_CENTRE = "Diagnostic Centre"
    OTHER = "Other"

class HealthcareFacility(Base):
    __tablename__ = "healthcare_facilities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    facility_type = Column(String, nullable=False, index=True)
    ownership = Column(String, nullable=True) # Public, Private, NGO
    
    # Location
    address = Column(String, nullable=True)
    village = Column(String, nullable=True)
    taluk = Column(String, nullable=True)
    district = Column(String, nullable=True, index=True)
    state = Column(String, nullable=True)
    pincode = Column(String, nullable=True, index=True)
    
    # Coordinates for mapping and distance calculation
    latitude = Column(Float, nullable=True, index=True)
    longitude = Column(Float, nullable=True, index=True)
    
    # Contact
    phone = Column(String, nullable=True)
    emergency_phone = Column(String, nullable=True)
    
    # Capabilities (JSON for flexible services list)
    services = Column(JSON, nullable=True)
    
    # Critical boolean flags for fast filtering
    emergency_available = Column(Boolean, default=False, index=True)
    ambulance_available = Column(Boolean, default=False)
    maternity_available = Column(Boolean, default=False)
    pharmacy_available = Column(Boolean, default=False)
    laboratory_available = Column(Boolean, default=False)
    telemedicine_available = Column(Boolean, default=False)
    
    opening_hours = Column(String, nullable=True)
    
    # Data integrity and tracking
    source = Column(String, nullable=True) # e.g. "OSM", "Govt API", "Manual"
    source_url = Column(String, nullable=True)
    source_record_id = Column(String, nullable=True, index=True)
    source_type = Column(String, nullable=True)
    verification_status = Column(String, default="UNVERIFIED", index=True) # DEMO, UNVERIFIED, VERIFIED, STALE
    
    verified_at = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String, default="active") # active, inactive, pending_verification
    
    created_at = Column(DateTime, default=datetime.utcnow)
