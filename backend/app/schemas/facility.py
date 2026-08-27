from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from app.models.facility import FacilityType

class FacilityBase(BaseModel):
    name: str
    facility_type: FacilityType
    ownership: Optional[str] = None
    address: Optional[str] = None
    village: Optional[str] = None
    taluk: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    emergency_phone: Optional[str] = None
    services: Optional[Any] = None
    emergency_available: bool = False
    ambulance_available: bool = False
    maternity_available: bool = False
    pharmacy_available: bool = False
    laboratory_available: bool = False
    telemedicine_available: bool = False
    opening_hours: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    source_record_id: Optional[str] = None
    source_type: Optional[str] = None
    verification_status: str = "UNVERIFIED"
    status: str = "active"

class FacilityCreate(FacilityBase):
    pass

class FacilityUpdate(BaseModel):
    name: Optional[str] = None
    facility_type: Optional[FacilityType] = None
    ownership: Optional[str] = None
    address: Optional[str] = None
    village: Optional[str] = None
    taluk: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    emergency_phone: Optional[str] = None
    services: Optional[Any] = None
    emergency_available: Optional[bool] = None
    ambulance_available: Optional[bool] = None
    maternity_available: Optional[bool] = None
    pharmacy_available: Optional[bool] = None
    laboratory_available: Optional[bool] = None
    telemedicine_available: Optional[bool] = None
    opening_hours: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    source_record_id: Optional[str] = None
    source_type: Optional[str] = None
    verification_status: Optional[str] = None
    status: Optional[str] = None

class FacilityOut(FacilityBase):
    id: int
    verified_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    created_at: datetime
    distance_km: Optional[float] = None  # To return distance in search

    class Config:
        orm_mode = True
        from_attributes = True
