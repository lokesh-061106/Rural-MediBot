import csv
import json
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel, validator, ValidationError

from app.models.facility import HealthcareFacility, FacilityType

class IngestStats(BaseModel):
    total_records: int = 0
    accepted: int = 0
    rejected: int = 0
    duplicates: int = 0
    inserted: int = 0
    updated: int = 0
    invalid_coordinates: int = 0

def normalize_facility_type(raw_type: str) -> FacilityType:
    raw_type = raw_type.upper().strip()
    if "PHC" in raw_type or "PRIMARY" in raw_type:
        return FacilityType.PHC
    if "CHC" in raw_type or "COMMUNITY" in raw_type:
        return FacilityType.CHC
    if "DISTRICT" in raw_type:
        return FacilityType.DISTRICT_HOSPITAL
    if "SUB" in raw_type or "SC" in raw_type:
        return FacilityType.SUB_CENTRE
    if "PRIVATE" in raw_type:
        return FacilityType.PRIVATE_HOSPITAL
    if "CLINIC" in raw_type:
        return FacilityType.CLINIC
    if "HOSPITAL" in raw_type:
        return FacilityType.GOVERNMENT_HOSPITAL
    return FacilityType.OTHER

def validate_coordinates(lat: Any, lon: Any) -> Tuple[bool, float, float]:
    try:
        lat = float(lat)
        lon = float(lon)
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return True, lat, lon
        return False, 0.0, 0.0
    except (ValueError, TypeError):
        return False, 0.0, 0.0

def process_facility_record(db: Session, record: Dict[str, Any], stats: IngestStats):
    stats.total_records += 1
    
    # 1. Validation
    name = str(record.get("name", "")).strip()
    if not name:
        stats.rejected += 1
        return
        
    source = str(record.get("source", "")).strip()
    source_type = str(record.get("source_type", "")).strip()
    if not source or not source_type:
        stats.rejected += 1
        return
        
    source_record_id = str(record.get("source_record_id", "")).strip()
    if not source_record_id:
        stats.rejected += 1
        return
        
    lat_valid, lat, lon = validate_coordinates(record.get("latitude"), record.get("longitude"))
    if not lat_valid:
        stats.invalid_coordinates += 1
        stats.rejected += 1
        return
        
    # 2. Normalization
    fac_type = normalize_facility_type(str(record.get("facility_type", "")))
    
    # 3. Deduplication and Upsert
    existing = db.query(HealthcareFacility).filter(
        HealthcareFacility.source == source,
        HealthcareFacility.source_record_id == source_record_id
    ).first()
    
    verification_status = str(record.get("verification_status", "UNVERIFIED")).strip().upper()
    if verification_status not in ["DEMO", "UNVERIFIED", "VERIFIED", "STALE"]:
        verification_status = "UNVERIFIED"

    is_emergency = str(record.get("emergency_available", "")).strip().lower() in ["true", "1", "yes"]

    if existing:
        stats.updated += 1
        stats.duplicates += 1 # it was already there
        existing.name = name
        existing.facility_type = fac_type
        existing.latitude = lat
        existing.longitude = lon
        existing.emergency_available = is_emergency
        existing.verification_status = verification_status
        existing.verified_at = datetime.utcnow()
        existing.status = "active"
    else:
        stats.inserted += 1
        new_fac = HealthcareFacility(
            name=name,
            facility_type=fac_type,
            latitude=lat,
            longitude=lon,
            emergency_available=is_emergency,
            source=source,
            source_type=source_type,
            source_record_id=source_record_id,
            verification_status=verification_status,
            verified_at=datetime.utcnow(),
            status="active"
        )
        db.add(new_fac)
        
    stats.accepted += 1

def ingest_json(db: Session, data: List[Dict[str, Any]]) -> IngestStats:
    stats = IngestStats()
    for record in data:
        process_facility_record(db, record, stats)
    db.commit()
    return stats

