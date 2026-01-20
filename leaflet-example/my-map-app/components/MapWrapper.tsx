'use client';

import dynamic from 'next/dynamic';

// This acts as the bridge. It is a Client Component, so it can disable SSR.
const Map = dynamic(() => import('./Map'), { 
  ssr: false,
  loading: () => <p>Loading map...</p>
});

export default function MapWrapper() {
  return <Map />;
}