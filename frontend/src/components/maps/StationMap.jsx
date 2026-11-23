import { useEffect, useMemo } from 'react'
import L from 'leaflet'
import { Link } from 'react-router-dom'
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import StatusBadge from '../ui/StatusBadge'

const STATUS_COLORS = {
  ONLINE: '#16a34a',
  DELAYED: '#d97706',
  OFFLINE: '#dc2626',
  MAINTENANCE: '#2563eb',
  UNKNOWN: '#64748b',
}

function markerIcon(status) {
  const color = STATUS_COLORS[status] || STATUS_COLORS.UNKNOWN
  return L.divIcon({
    className: '',
    html: `<div style="background:${color};width:18px;height:18px;border-radius:50%;border:3px solid white;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  })
}

// Moves the viewport when the administrator selects a station in the sidebar.
function FocusOnStation({ stationId, stations }) {
  const map = useMap()
  useEffect(() => {
    const target = stations.find((station) => station.id === stationId)
    if (target && target.latitude != null && target.longitude != null) {
      map.flyTo([Number(target.latitude), Number(target.longitude)], 12, { duration: 0.8 })
    }
  }, [stationId, stations, map])
  return null
}

/** Leaflet map using OpenStreetMap tiles and real station coordinates. */
export default function StationMap({ stations, selectedStationId, onMarkerClick }) {
  const mappable = useMemo(
    () => stations.filter((station) => station.latitude != null && station.longitude != null),
    [stations],
  )

  const center = useMemo(() => {
    if (mappable.length === 0) return [6.11582, 124.846231] // Salacafe reference
    const lat = mappable.reduce((sum, s) => sum + Number(s.latitude), 0) / mappable.length
    const lng = mappable.reduce((sum, s) => sum + Number(s.longitude), 0) / mappable.length
    return [lat, lng]
  }, [mappable])

  return (
    <MapContainer
      center={center}
      zoom={mappable.length > 1 ? 6 : 10}
      scrollWheelZoom
      className="h-[520px] w-full rounded-lg"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FocusOnStation stationId={selectedStationId} stations={mappable} />
      {mappable.map((station) => (
        <Marker
          key={station.id}
          position={[Number(station.latitude), Number(station.longitude)]}
          icon={markerIcon(station.operational_status)}
          eventHandlers={{ click: () => onMarkerClick && onMarkerClick(station.id) }}
        >
          <Popup>
            <div className="min-w-[180px] text-sm">
              <p className="font-semibold text-slate-900">{station.name}</p>
              <p className="text-xs text-slate-600">{station.station_code} · {station.site_name || '—'}</p>
              <p className="text-xs text-slate-600">
                {Number(station.latitude).toFixed(5)}, {Number(station.longitude).toFixed(5)}
              </p>
              <div className="my-2"><StatusBadge status={station.operational_status} /></div>
              <Link to={`/stations/${station.id}`} className="text-xs font-medium text-brand-600 underline">
                View station details
              </Link>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  )
}
