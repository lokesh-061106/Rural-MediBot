from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from math import radians, cos, sin, asin, sqrt
from app.models.facility import HealthcareFacility, FacilityType

def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Calculate the great circle distance in kilometers between two points on the earth."""
    if None in (lon1, lat1, lon2, lat2):
        return float('inf')
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371 # Radius of earth in kilometers
    return c * r

class FacilityNetworkService:
    @staticmethod
    def get_facility_navigation_data(facility: HealthcareFacility) -> Optional[Dict[str, Any]]:
        if facility.latitude is None or facility.longitude is None:
            return None
            
        maps_url = f"https://www.openstreetmap.org/?mlat={facility.latitude}&mlon={facility.longitude}#map=18/{facility.latitude}/{facility.longitude}"
        return {
            "latitude": facility.latitude,
            "longitude": facility.longitude,
            "maps_url": maps_url
        }

    @staticmethod
    def format_facility_result(facility: HealthcareFacility, distance_km: float) -> Dict[str, Any]:
        return {
            "facility_id": str(facility.id),
            "name": facility.name,
            "distance_km": round(distance_km, 2),
            "facility_type": facility.facility_type,
            "emergency_available": facility.emergency_available,
            "ambulance_available": facility.ambulance_available,
            "verification_status": facility.verification_status or "UNVERIFIED",
            "source": facility.source,
            "navigation": FacilityNetworkService.get_facility_navigation_data(facility)
        }

    @staticmethod
    def find_nearby_facilities(
        db: Session,
        latitude: float,
        longitude: float,
        radius_km: float = 20.0,
        facility_type: Optional[FacilityType] = None,
        emergency: Optional[bool] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
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
                results.append((f, dist))
                
        # Sort logic
        results = FacilityNetworkService.rank_facilities(results)
        
        return [FacilityNetworkService.format_facility_result(f, dist) for f, dist in results[:limit]]

    @staticmethod
    def find_emergency_facilities(
        db: Session,
        latitude: float,
        longitude: float,
        radius_km: float = 50.0,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        return FacilityNetworkService.find_nearby_facilities(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            emergency=True,
            limit=limit
        )

    @staticmethod
    def rank_facilities(facilities_with_dist: List[tuple]) -> List[tuple]:
        """
        Rank facilities.
        1. Distance
        2. Emergency capability (prioritize True)
        3. Ambulance availability
        """
        return sorted(facilities_with_dist, key=lambda x: (
            x[1], # distance
            not x[0].emergency_available, # False sorts before True, so we negate
            not x[0].ambulance_available
        ))

