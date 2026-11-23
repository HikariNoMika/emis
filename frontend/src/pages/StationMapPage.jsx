import { useState } from 'react'
import { Link } from 'react-router-dom'
import StationMap from '../components/maps/StationMap'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import PageHeader from '../components/ui/PageHeader'
import StatusBadge from '../components/ui/StatusBadge'
import { useMapStations } from '../hooks/useStations'
import { extractError } from '../services/api'

const STATUSES = ['ONLINE', 'DELAYED', 'OFFLINE', 'MAINTENANCE', 'UNKNOWN']

export default function StationMapPage() {
  const query = useMapStations()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [selectedId, setSelectedId] = useState(null)

  const all = query.data || []
  const filtered = all.filter((station) => {
    const matchesStatus = !status || station.operational_status === status
    const term = search.toLowerCase()
    const matchesSearch =
      !term ||
      station.name.toLowerCase().includes(term) ||
      station.station_code.toLowerCase().includes(term) ||
      (station.site_name || '').toLowerCase().includes(term)
    return matchesStatus && matchesSearch
  })

  return (
    <div>
      <PageHeader
        title="Monitoring Station Map"
        description="Geographic view of registered stations. Markers are coloured by operational status."
      />

      <div className="mb-4 flex flex-col gap-3 sm:flex-row">
        <input
          className="input flex-1"
          placeholder="Search stations…"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <select className="input sm:w-56" value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">All statuses</option>
          {STATUSES.map((item) => <option key={item}>{item}</option>)}
        </select>
      </div>

      {query.isLoading ? (
        <LoadingSpinner label="Loading stations…" />
      ) : query.isError ? (
        <ErrorState message={extractError(query.error)} onRetry={query.refetch} />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
          <div className="card max-h-[520px] overflow-y-auto">
            <p className="border-b border-slate-200 px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
              {filtered.length} station{filtered.length === 1 ? '' : 's'}
            </p>
            {filtered.length === 0 ? (
              <p className="px-4 py-6 text-sm text-slate-500">No stations match your filters.</p>
            ) : (
              <div className="divide-y divide-slate-100">
                {filtered.map((station) => (
                  <button
                    key={station.id}
                    type="button"
                    onClick={() => setSelectedId(station.id)}
                    className={`block w-full px-4 py-3 text-left hover:bg-slate-50 ${
                      selectedId === station.id ? 'bg-brand-50' : ''
                    }`}
                  >
                    <p className="text-sm font-medium text-slate-800">{station.name}</p>
                    <p className="text-xs text-slate-500">{station.station_code}</p>
                    <div className="mt-1">
                      <StatusBadge status={station.operational_status} />
                    </div>
                    {station.latitude == null && (
                      <p className="mt-1 text-xs text-amber-600">No GPS coordinates</p>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div>
            <StationMap
              stations={filtered}
              selectedStationId={selectedId}
              onMarkerClick={setSelectedId}
            />
            <p className="mt-2 text-xs text-slate-500">
              Stations without valid GPS coordinates are listed but not plotted. Click a marker for details.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
