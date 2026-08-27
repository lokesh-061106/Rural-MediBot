"use client";
import { useState, useEffect } from 'react';
import { HospitalService } from '../../../lib/services/HospitalService';
import { useConnectivity } from '../../../hooks/useConnectivity';
import Link from 'next/link';
import { ArrowLeft, Navigation, Phone, Clock, AlertCircle } from 'lucide-react';

export default function FacilityDetails({ params }) {
  const { id } = params;
  const [facility, setFacility] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);
  const { isOnline } = useConnectivity();

  useEffect(() => {
    async function loadData() {
      try {
        const res = await HospitalService.getHospitalDetails(id);
        if (res && res.data) {
          setFacility(res.data);
          const isSaved = await HospitalService.isHospitalSaved(parseInt(id));
          setSaved(isSaved);
        } else {
          setError("Facility not found.");
        }
      } catch (e) {
        setError("Error loading facility details.");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [id]);

  const toggleSave = async () => {
    if (saved) {
      await HospitalService.unSaveHospital(parseInt(id));
      setSaved(false);
    } else {
      await HospitalService.saveHospital(facility);
      setSaved(true);
    }
  };

  if (loading) return <div className="p-8 text-center">Loading facility details...</div>;
  if (error || !facility) return <div className="p-8 text-center text-red-500">{error || "Not found"}</div>;

  return (
    <div className="max-w-4xl mx-auto p-4">
      <Link href="/facilities" className="flex items-center text-blue-600 mb-6 hover:underline">
        <ArrowLeft className="w-4 h-4 mr-1" /> Back to Search
      </Link>
      
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="p-6 border-b border-gray-100">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-2xl font-bold text-gray-800">{facility.name}</h1>
              <p className="text-gray-600 text-lg mt-1">{facility.facility_type}</p>
            </div>
            <button 
              onClick={toggleSave}
              className={`px-4 py-2 rounded font-medium ${saved ? 'bg-gray-200 text-gray-800' : 'bg-blue-600 text-white'}`}
            >
              {saved ? 'Saved' : 'Save'}
            </button>
          </div>

          {facility.emergency_available && (
            <div className="mt-4 flex items-center text-red-600 bg-red-50 p-3 rounded-lg">
              <AlertCircle className="w-5 h-5 mr-2" />
              <strong>Emergency Services Available</strong>
            </div>
          )}
        </div>
        
        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <h2 className="text-lg font-semibold mb-4 border-b pb-2">Contact & Location</h2>
            
            <div className="space-y-4">
              <div>
                <strong className="block text-gray-500 text-sm">Address</strong>
                <p>{[facility.address, facility.village, facility.taluk, facility.district, facility.state, facility.pincode].filter(Boolean).join(', ')}</p>
              </div>

              {facility.phone && (
                <div className="flex items-center">
                  <Phone className="w-4 h-4 mr-2 text-gray-400" />
                  <a href={`tel:${facility.phone}`} className="text-blue-600 hover:underline">{facility.phone}</a>
                </div>
              )}

              {facility.emergency_phone && (
                <div className="flex items-center">
                  <AlertCircle className="w-4 h-4 mr-2 text-red-500" />
                  <a href={`tel:${facility.emergency_phone}`} className="text-red-600 font-bold hover:underline">Emergency: {facility.emergency_phone}</a>
                </div>
              )}
              
              {facility.opening_hours && (
                <div className="flex items-center text-gray-700">
                  <Clock className="w-4 h-4 mr-2 text-gray-400" />
                  {facility.opening_hours}
                </div>
              )}
            </div>

            <div className="mt-6">
              <a 
                href={HospitalService.getDirectionsLink(facility.latitude, facility.longitude)}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full flex items-center justify-center py-3 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition"
              >
                <Navigation className="w-5 h-5 mr-2" /> Get Directions
              </a>
            </div>
          </div>

          <div>
            <h2 className="text-lg font-semibold mb-4 border-b pb-2">Capabilities</h2>
            <ul className="space-y-3">
              <li className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <span>Ambulance</span>
                {facility.ambulance_available ? <span className="text-green-600 font-bold">Yes</span> : <span className="text-gray-400">No</span>}
              </li>
              <li className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <span>Maternity Care</span>
                {facility.maternity_available ? <span className="text-green-600 font-bold">Yes</span> : <span className="text-gray-400">No</span>}
              </li>
              <li className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <span>Pharmacy</span>
                {facility.pharmacy_available ? <span className="text-green-600 font-bold">Yes</span> : <span className="text-gray-400">No</span>}
              </li>
              <li className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <span>Laboratory</span>
                {facility.laboratory_available ? <span className="text-green-600 font-bold">Yes</span> : <span className="text-gray-400">No</span>}
              </li>
              <li className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <span>Telemedicine</span>
                {facility.telemedicine_available ? <span className="text-green-600 font-bold">Yes</span> : <span className="text-gray-400">No</span>}
              </li>
            </ul>
            
            {facility.last_updated && (
              <p className="text-xs text-gray-400 mt-6 text-right">
                Information last updated: {new Date(facility.last_updated).toLocaleDateString()}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
