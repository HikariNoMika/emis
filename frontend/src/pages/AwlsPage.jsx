import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import { useStations } from '../hooks/useStations'
import { extractError } from '../services/api'
import { findStationByName } from '../utils/stations'
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
 * Automated Water Level Station. This view is locked to NAMNAMA; CSV uploads
 * for that station supply the water-level readings.
 */
export default function AwlsPage() {
  const stationsQuery = useStations({ page: 1, per_page: 100 })

  if (stationsQuery.isLoading) return <LoadingSpinner label="Loading AWLS…" />
  if (stationsQuery.isError) {
    return (
      <ErrorState
        message={extractError(stationsQuery.error)}
        onRetry={stationsQuery.refetch}
      />
    )
  }

  const station = findStationByName(stationsQuery.data?.data || [], 'NAMNAMA')

  if (!station) {
    return (
      <EmptyState
        title="NAMNAMA station not found"
        description="Upload a water-level CSV for NAMNAMA from Data Management; the station and its readings will appear here."
      />
    )
  }

  return (
    <AwsStationPage
      fixedStationId={station.id}
      allowedTypeCodes={AWLS_TYPE_CODES}
      brand="AWLS"
      description="Automated Water Level Station: water-level readings, statistics and trends for NAMNAMA."
    />
  )
}
