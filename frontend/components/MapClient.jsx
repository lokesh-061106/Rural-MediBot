"use client";

import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import Link from "next/link";
import { HospitalService } from "../lib/services/HospitalService";
import { ExternalLink } from "lucide-react";

// Fix Leaflet's default icon path issues in Next.js
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

// Custom icons
const emergencyIcon = new L.Icon({
  iconUrl:
    "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const defaultIcon = new L.Icon({
  iconUrl:
    "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const userIcon = new L.Icon({
  iconUrl:
    "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

function FitFacilities({ center, zoom, facilities, userLocation }) {
  const map = useMap();

  useEffect(() => {
    const points = facilities
      .filter(
        (facility) =>
          Number.isFinite(facility.latitude) &&
          Number.isFinite(facility.longitude),
      )
      .map((facility) => [facility.latitude, facility.longitude]);

    if (userLocation)
      points.push([userLocation.latitude, userLocation.longitude]);

    if (points.length > 1) {
      map.fitBounds(points, { padding: [32, 32], maxZoom: 14 });
    } else {
      map.setView(center, zoom);
    }
  }, [center, zoom, facilities, userLocation, map]);

  return null;
}

export default function MapClient({
  facilities = [],
  userLocation,
  zoom = 12,
}) {
  const defaultCenter = [19.076, 72.8777]; // Default Mumbai
  const center = userLocation
    ? [userLocation.latitude, userLocation.longitude]
    : defaultCenter;

  return (
    <div className="h-full w-full rounded-xl overflow-hidden shadow-sm border border-gray-200">
      <MapContainer
        center={center}
        zoom={zoom}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitFacilities
          center={center}
          zoom={zoom}
          facilities={facilities}
          userLocation={userLocation}
        />

        {userLocation && (
          <Marker
            position={[userLocation.latitude, userLocation.longitude]}
            icon={userIcon}
          >
            <Popup>
              <strong>Your Location</strong>
            </Popup>
          </Marker>
        )}

        {facilities.map((facility) =>
          facility.latitude && facility.longitude ? (
            <Marker
              key={facility.id}
              position={[facility.latitude, facility.longitude]}
              icon={facility.emergency_available ? emergencyIcon : defaultIcon}
            >
              <Popup>
                <div className="p-1">
                  <h3 className="font-bold text-sm">{facility.name}</h3>
                  <p className="text-xs text-gray-600 mb-2">
                    {facility.facility_type}
                  </p>

                  {facility.distance_km && (
                    <p className="text-xs mb-2">
                      {facility.distance_km} km away
                    </p>
                  )}

                  <div className="flex flex-col gap-2 mt-2">
                    <Link
                      href={`/facilities/${facility.id}`}
                      className="text-xs text-blue-600 font-medium hover:underline"
                    >
                      View Details
                    </Link>
                    <a
                      href={HospitalService.getDirectionsLink(
                        facility.latitude,
                        facility.longitude,
                      )}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs flex items-center text-green-600 font-medium hover:underline"
                    >
                      Directions <ExternalLink className="w-3 h-3 ml-1" />
                    </a>
                  </div>
                </div>
              </Popup>
            </Marker>
          ) : null,
        )}
      </MapContainer>
    </div>
  );
}
