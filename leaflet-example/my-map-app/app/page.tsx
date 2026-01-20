// Notice: We import MapWrapper, NOT Map
import MapWrapper from '@/components/MapWrapper';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <div className="z-10 w-full max-w-5xl items-center justify-between font-mono text-sm lg:flex">
        <h1 className="text-4xl font-bold mb-8">Next.js + Leaflet</h1>
      </div>

      <div className="w-full h-[500px] border-2 border-gray-300 rounded-lg overflow-hidden">
        <MapWrapper />
      </div>
    </main>
  );
}