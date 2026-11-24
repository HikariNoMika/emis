import { useState } from 'react'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import { useStations } from '../hooks/useStations'
import { extractError } from '../services/api'
import AwsStationPage from './AwsStationPage'

// The water-level station uses its own sensors — only these parameters are
// offered on the AWLS page, never the weather-station parameters.
const AWLS_TYPE_CODES = [
  'water_level',
  'water_temperature',
  'ec',
  'system_battery_voltage',
  'system_temperature',
]

/**
 * Automated Water Level Station view. Shows every station tagged with the
 * AWLS destination type (set in the import preview or station settings).
 */
export default function AwlsPage() {
  const stationsQuery = useStations({ page: 1, per_page: 100 })
  const [selectedId, setSelectedId] = useState(null)

  if (stationsQuery.isLoading) return <LoadingSpinner label="Loading AWLS…" />
  if (stationsQuery.isError) {
    return (
      <ErrorState
        message={extractError(stationsQuery.error)}
        onRetry={stationsQuery.refetch}
      />
    )
  }

  const awlsStations = (stationsQuery.data?.data || []).filter(
    (station) => station.station_type === 'AWLS',
  )

  if (awlsStations.length === 0) {
    return (
      <EmptyState
        title="No water-level stations yet"
        description="Set a station's Destination type to AWLS in the import preview or station settings, then upload its water-level file."
      />
    )
  }

  const station = awlsStations.find((item) => item.id === selectedId) || awlsStations[0]

  return (
    <div>
      {awlsStations.length > 1 && (
        <div className="card mb-4 flex items-center gap-3 p-3">
          <label className="label" htmlFor="awls-station">Water-level station</label>
          <select
            id="awls-station"
            className="input w-72"
            value={station.id}
            onChange={(event) => setSelectedId(Number(event.target.value))}
          >
            {awlsStations.map((item) => (
              <option key={item.id} value={item.id}>
                {item.station_code} — {item.name}
              </option>
            ))}
          </select>
        </div>
      )}
      <AwsStationPage
        key={station.id}
        fixedStationId={station.id}
        allowedTypeCodes={AWLS_TYPE_CODES}
        brand="AWLS"
        description="Automated Water Level Station: water-level readings, statistics and trends."
      />
    </div>
  )
}
