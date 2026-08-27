"use client";

import dynamic from 'next/dynamic';

const MapClient = dynamic(() => import('./MapClient'), { 
  ssr: false, 
  loading: () => <div className="h-full w-full flex items-center justify-center bg-gray-100 rounded-xl text-gray-500">Loading Map...</div>
});

export default function Map(props) {
  return <MapClient {...props} />;
}
