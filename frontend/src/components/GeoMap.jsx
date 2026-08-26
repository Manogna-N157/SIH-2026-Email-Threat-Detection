import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapPin, AlertCircle } from 'lucide-react';

// Fix default Leaflet icon paths in React/Vite builds
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

export default function GeoMap({ locationData, title = 'Infrastructure GeoLocation Map', height = '350px' }) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markerRef = useRef(null);

  // Extract lat, lng, ip, city, country, isp, org
  const lat = locationData?.latitude ?? locationData?.lat ?? locationData?.probable_infrastructure_location?.latitude;
  const lng = locationData?.longitude ?? locationData?.lng ?? locationData?.probable_infrastructure_location?.longitude;
  const ip = locationData?.ip || locationData?.probable_infrastructure_location?.ip || 'N/A';
  const city = locationData?.city || locationData?.probable_infrastructure_location?.city || 'N/A';
  const region = locationData?.region || locationData?.probable_infrastructure_location?.region || '';
  const country = locationData?.country || locationData?.probable_infrastructure_location?.country || 'N/A';
  const isp = locationData?.isp || locationData?.probable_infrastructure_location?.isp || locationData?.organization || locationData?.probable_infrastructure_location?.organization || 'N/A';

  const isValidLocation =
    typeof lat === 'number' &&
    typeof lng === 'number' &&
    !isNaN(lat) &&
    !isNaN(lng) &&
    (lat !== 0 || lng !== 0);

  useEffect(() => {
    if (!isValidLocation || !mapContainerRef.current) return;

    // Initialize Leaflet map instance if not created yet
    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        center: [lat, lng],
        zoom: 6,
        zoomControl: true,
      });

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(map);

      mapInstanceRef.current = map;
    } else {
      // Re-center map if coordinates change
      mapInstanceRef.current.setView([lat, lng], 6);
    }

    // Remove existing marker if any
    if (markerRef.current) {
      markerRef.current.remove();
    }

    // Create marker with detailed popup
    const popupContent = `
      <div style="font-family: sans-serif; font-size: 13px; line-height: 1.4; padding: 4px;">
        <h4 style="margin: 0 0 6px 0; color: #1e293b; font-size: 14px; border-bottom: 1px solid #cbd5e1; padding-bottom: 4px;">
          Detected Infrastructure Location
        </h4>
        <div><strong>IP Address:</strong> <code>${ip}</code></div>
        <div><strong>City:</strong> ${city}${region ? `, ${region}` : ''}</div>
        <div><strong>Country:</strong> ${country}</div>
        <div><strong>Latitude:</strong> ${lat}</div>
        <div><strong>Longitude:</strong> ${lng}</div>
        <div><strong>ISP/Org:</strong> ${isp}</div>
      </div>
    `;

    const marker = L.marker([lat, lng])
      .addTo(mapInstanceRef.current)
      .bindPopup(popupContent)
      .openPopup();

    markerRef.current = marker;

    return () => {
      // Clean up map instance on unmount
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [lat, lng, ip, city, region, country, isp, isValidLocation]);

  if (!isValidLocation) {
    return (
      <div className="geomap-card card" style={{ padding: '20px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
        <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '0 0 12px 0', fontSize: '15px', color: '#1e293b' }}>
          <MapPin size={18} color="#2563eb" /> {title}
        </h4>
        <div className="alert alert-info" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <AlertCircle size={18} />
          <span>Location data unavailable for this case.</span>
        </div>
      </div>
    );
  }

  return (
    <div className="geomap-card card" style={{ padding: '16px', background: '#ffffff', borderRadius: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: 0, fontSize: '15px', color: '#1e293b' }}>
          <MapPin size={18} color="#2563eb" /> {title}
        </h4>
        <span style={{ fontSize: '12px', background: '#e0f2fe', color: '#0369a1', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
          {city}, {country} ({lat.toFixed(4)}, {lng.toFixed(4)})
        </span>
      </div>

      <div
        ref={mapContainerRef}
        style={{
          width: '100%',
          height: height,
          borderRadius: '6px',
          border: '1px solid #cbd5e1',
          overflow: 'hidden',
          zIndex: 1,
        }}
      />
    </div>
  );
}
