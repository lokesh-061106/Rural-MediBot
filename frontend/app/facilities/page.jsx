"use client";

import { useState, useEffect } from "react";
import { HospitalService } from "../../lib/services/HospitalService";
import { useLocation } from "../../hooks/useLocation";
import Map from "../../components/Map";
import Link from "next/link";
import { Search, MapPin, AlertCircle, Phone, Navigation } from "lucide-react";
import { useConnectivity } from "../../hooks/useConnectivity";

export default function FacilitiesPage() {
  const {
    location,
    error: locError,
    loading: locLoading,
    requestLocation,
  } = useLocation();
  const { isOnline } = useConnectivity();
  const [facilities, setFacilities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filterType, setFilterType] = useState("");
  const [filterEmergency, setFilterEmergency] = useState(false);
  const [dataSource, setDataSource] = useState(null); // 'online' or 'offline'

  const fetchAllFacilities = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await HospitalService.findAllHospitals(
        filterType || null,
        filterEmergency ? true : null,
      );
      setFacilities(response.data);
      setDataSource(response.source === "online" ? "directory" : "offline");
    } catch (err) {
      setError("Failed to fetch facilities.");
    } finally {
      setLoading(false);
    }
  };

  const fetchFacilities = async (lat, lng) => {
    setLoading(true);
    setError(null);
    try {
      const response = await HospitalService.findNearbyHospitals(
        lat,
        lng,
        30,
        filterType || null,
        filterEmergency ? true : null,
      );
      if (response.data.length === 0 && !filterType && !filterEmergency) {
        await fetchAllFacilities();
      } else {
        setFacilities(response.data);
        setDataSource(response.source);
      }
    } catch (err) {
      setError("Failed to fetch facilities.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (location) {
      fetchFacilities(location.latitude, location.longitude);
    } else if (!isOnline) {
      fetchAllFacilities();
    }
  }, [location, filterType, filterEmergency, isOnline]);

  return (
    <div className="flex flex-col h-full bg-gray-50 p-4 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-800 mb-4">
        Find Healthcare Facilities
      </h1>

      {!isOnline && (
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4 rounded shadow-sm">
          <div className="flex items-center">
            <AlertCircle className="h-5 w-5 text-yellow-500 mr-2" />
            <p className="text-sm text-yellow-700">
              Offline mode is active. Facility directory and emergency chat
              remain available without internet.
            </p>
          </div>
        </div>
      )}

      {/* Location request block */}
      {!location && !locLoading && (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 mb-6 flex flex-col items-center text-center">
          <MapPin className="h-12 w-12 text-blue-500 mb-4" />
          <h2 className="text-lg font-semibold mb-2">Location Required</h2>
          <p className="text-gray-600 mb-4">
            Please share your location to find nearby hospitals and clinics.
          </p>
          <button
            onClick={requestLocation}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition"
          >
            Use My Current Location
          </button>
          <button
            onClick={fetchAllFacilities}
            className="mt-3 px-6 py-2 border border-blue-600 text-blue-700 rounded-lg font-medium hover:bg-blue-50 transition"
          >
            Browse All Facilities
          </button>
          {locError && <p className="text-red-500 mt-4 text-sm">{locError}</p>}
        </div>
      )}

      {locLoading && (
        <div className="flex justify-center p-8 text-gray-500">
          Getting location...
        </div>
      )}

      {(location || facilities.length > 0) && (
        <div className="flex flex-col lg:flex-row gap-6 h-[calc(100vh-180px)] min-h-[600px]">
          {/* Sidebar / List View */}
          <div className="w-full lg:w-1/3 flex flex-col gap-4 overflow-hidden">
            {/* Filters */}
            <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
              <div className="flex justify-between items-center mb-3">
                <h3 className="font-semibold text-gray-700">Filters</h3>
              </div>
              <div className="space-y-3">
                <select
                  className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value)}
                >
                  <option value="">All Facility Types</option>
                  <option value="PHC">Primary Health Centre (PHC)</option>
                  <option value="CHC">Community Health Centre (CHC)</option>
                  <option value="District Hospital">District Hospital</option>
                  <option value="Clinic">Clinic</option>
                  <option value="Pharmacy">Pharmacy</option>
                </select>

                <label className="flex items-center space-x-2 text-sm text-gray-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={filterEmergency}
                    onChange={(e) => setFilterEmergency(e.target.checked)}
                    className="rounded text-red-600 focus:ring-red-500"
                  />
                  <span>Emergency Available Only</span>
                </label>
              </div>
            </div>

            {/* List */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 flex-1 overflow-y-auto">
              <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50 sticky top-0">
                <h3 className="font-semibold text-gray-700">
                  {facilities.length} Results
                </h3>
                {dataSource === "offline" && (
                  <span className="text-xs bg-gray-200 px-2 py-1 rounded text-gray-700">
                    Cached
                  </span>
                )}
                {dataSource === "directory" && (
                  <span className="text-xs bg-blue-100 px-2 py-1 rounded text-blue-700">
                    Directory
                  </span>
                )}
              </div>

              {loading && (
                <div className="p-4 text-center text-gray-500">
                  Searching...
                </div>
              )}
              {error && (
                <div className="p-4 text-center text-red-500">{error}</div>
              )}

              {!loading && facilities.length === 0 && (
                <div className="p-8 text-center text-gray-500">
                  No facilities found nearby. Try expanding your search or
                  removing filters.
                  <button
                    onClick={fetchAllFacilities}
                    className="block mx-auto mt-3 text-blue-700 hover:underline"
                  >
                    Browse all facilities
                  </button>
                </div>
              )}

              <div className="divide-y divide-gray-100">
                {facilities.map((f) => (
                  <div key={f.id} className="p-4 hover:bg-gray-50 transition">
                    <div className="flex justify-between items-start mb-1">
                      <Link
                        href={`/facilities/${f.id}`}
                        className="font-bold text-blue-700 hover:underline"
                      >
                        {f.name}
                      </Link>
                      {f.distance_km && (
                        <span className="text-xs font-semibold text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                          {f.distance_km} km
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 mb-2">
                      {f.facility_type}
                    </p>

                    {f.emergency_available && (
                      <span className="inline-block px-2 py-1 bg-red-100 text-red-700 text-xs rounded font-medium mb-3">
                        Emergency Services
                      </span>
                    )}

                    <div className="flex gap-2 mt-2">
                      <a
                        href={HospitalService.getDirectionsLink(
                          f.latitude,
                          f.longitude,
                        )}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 flex items-center justify-center gap-1 py-1.5 px-3 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded transition"
                      >
                        <Navigation className="w-4 h-4" /> Directions
                      </a>
                      {f.phone && (
                        <a
                          href={`tel:${f.phone}`}
                          className="flex-1 flex items-center justify-center gap-1 py-1.5 px-3 bg-green-50 hover:bg-green-100 text-green-700 text-sm font-medium rounded transition"
                        >
                          <Phone className="w-4 h-4" /> Call
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Map View */}
          <div className="w-full lg:w-2/3 h-[400px] lg:h-full">
            {isOnline ? (
              <Map facilities={facilities} userLocation={location} />
            ) : (
              <div className="h-full w-full rounded-xl border border-yellow-300 bg-yellow-50 p-8 flex flex-col items-center justify-center text-center text-yellow-900">
                <MapPin className="h-10 w-10 mb-3" />
                <h2 className="font-semibold text-lg">
                  Offline facility directory
                </h2>
                <p className="mt-2 max-w-md text-sm">
                  Map tiles need internet, but the facility list, phone numbers,
                  saved hospitals, and offline emergency triage are available.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
