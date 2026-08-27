from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from math import radians, cos, sin, asin, sqrt

from app.db.database import get_db
from app.models.facility import HealthcareFacility, FacilityType
from app.schemas.facility import FacilityCreate, FacilityUpdate, FacilityOut
from app.api.deps import get_current_user, get_current_active_user, require_role
from app.models.user import User

router = APIRouter()

# Haversine distance for basic proximity calculation without PostGIS
def haversine(lon1, lat1, lon2, lat2):
    if None in (lon1, lat1, lon2, lat2):
        return float('inf')
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371 # Radius of earth in kilometers
    return c * r

@router.get("/", response_model=List[FacilityOut])
def get_facilities(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    facility_type: Optional[FacilityType] = None,
    district: Optional[str] = None,
    pincode: Optional[str] = None,
    emergency: Optional[bool] = None
):
    query = db.query(HealthcareFacility).filter(HealthcareFacility.status == "active")
    if facility_type:
        query = query.filter(HealthcareFacility.facility_type == facility_type)
    if district:
        query = query.filter(HealthcareFacility.district.ilike(f"%{district}%"))
    if pincode:
        query = query.filter(HealthcareFacility.pincode == pincode)
    if emergency is not None:
        query = query.filter(HealthcareFacility.emergency_available == emergency)
        
    return query.offset(skip).limit(limit).all()

@router.get("/nearby", response_model=List[FacilityOut])
def get_nearby_facilities(
    latitude: float,
    longitude: float,
    radius_km: float = 20.0,
    facility_type: Optional[FacilityType] = None,
    emergency: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    # Fetch all, compute distance in Python (simplest for SQLite compat without PostGIS)
    # Optimization: Filter by a bounding box first
    lat_diff = radius_km / 111.0 # 1 deg ~ 111km
    lon_diff = radius_km / (111.0 * cos(radians(latitude))) if cos(radians(latitude)) != 0 else 1
    
    query = db.query(HealthcareFacility).filter(
        HealthcareFacility.status == "active",
        HealthcareFacility.latitude >= latitude - lat_diff,
        HealthcareFacility.latitude <= latitude + lat_diff,
        HealthcareFacility.longitude >= longitude - lon_diff,
        HealthcareFacility.longitude <= longitude + lon_diff
    )
    
    if facility_type:
        query = query.filter(HealthcareFacility.facility_type == facility_type)
    if emergency is not None:
        query = query.filter(HealthcareFacility.emergency_available == emergency)
        
    candidates = query.all()
    results = []
    for f in candidates:
        dist = haversine(longitude, latitude, f.longitude, f.latitude)
        if dist <= radius_km:
            f.distance_km = round(dist, 2)
            results.append(f)
            
    # Sort by distance
    results.sort(key=lambda x: x.distance_km)
    return results

@router.get("/emergency", response_model=List[FacilityOut])
def get_emergency_facilities(
    latitude: float,
    longitude: float,
    db: Session = Depends(get_db)
):
    return get_nearby_facilities(latitude, longitude, radius_km=50.0, emergency=True, db=db)

@router.get("/emergency/nearby")
def get_emergency_facilities_structured(
    latitude: float,
    longitude: float,
    radius_km: float = 50.0,
    limit: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    from app.services.facility_network import FacilityNetworkService
    return FacilityNetworkService.find_emergency_facilities(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        limit=limit
    )

@router.get("/{facility_id}", response_model=FacilityOut)
def get_facility(facility_id: int, db: Session = Depends(get_db)):
    facility = db.query(HealthcareFacility).filter(HealthcareFacility.id == facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    return facility

@router.post("/", response_model=FacilityOut)
def create_facility(
    facility: FacilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    db_facility = HealthcareFacility(**facility.model_dump())
    db.add(db_facility)
    db.commit()
    db.refresh(db_facility)
    return db_facility

@router.put("/{facility_id}", response_model=FacilityOut)
def update_facility(
    facility_id: int,
    facility: FacilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    db_facility = db.query(HealthcareFacility).filter(HealthcareFacility.id == facility_id).first()
    if not db_facility:
        raise HTTPException(status_code=404, detail="Facility not found")
        
    update_data = facility.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_facility, key, value)
        
    db.commit()
    db.refresh(db_facility)
    return db_facility

@router.delete("/{facility_id}", response_model=dict)
def delete_facility(
    facility_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    from app.models.user import AuditLog
    db_facility = db.query(HealthcareFacility).filter(HealthcareFacility.id == facility_id).first()
    if not db_facility:
        raise HTTPException(status_code=404, detail="Facility not found")
        
    db_facility.status = "inactive"
    db.commit()
    
    log = AuditLog(user_id=current_user.id, action="FACILITY_DEACTIVATED", resource="Facility", resource_id=str(facility_id))
    db.add(log)
    db.commit()
    
    return {"status": "success", "message": "Facility deactivated successfully"}

@router.post("/{facility_id}/reactivate", response_model=dict)
def reactivate_facility(
    facility_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    from app.models.user import AuditLog
    db_facility = db.query(HealthcareFacility).filter(HealthcareFacility.id == facility_id).first()
    if not db_facility:
        raise HTTPException(status_code=404, detail="Facility not found")
        
    db_facility.status = "active"
    db.commit()
    
    log = AuditLog(user_id=current_user.id, action="FACILITY_REACTIVATED", resource="Facility", resource_id=str(facility_id))
    db.add(log)
    db.commit()
    
    return {"status": "success", "message": "Facility reactivated successfully"}
