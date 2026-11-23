import { useState } from 'react'
import DataTable from '../components/ui/DataTable'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import PageHeader from '../components/ui/PageHeader'
import StatusBadge from '../components/ui/StatusBadge'
import { useLatestMeasurements } from '../hooks/useMeasurements'
import { useStations } from '../hooks/useStations'
import { extractError } from '../services/api'
import measurementService from '../services/measurementService'

export default function LatestMonitoringPage() {
  const [stationId, setStationId] = useState('')
  const stationsQuery = useStations({ page: 1, per_page: 100 })
  const query = useLatestMeasurements(stationId ? { station_id: stationId } : {})

  const columns = [
    { key: 'type', label: 'Parameter', render: (row) => `#${row.measurement_type_id}` },
    {
      key: 'value', label: 'Value',
      render: (row) => `${row.normalized_value ?? row.original_value ?? '—'} ${row.unit || ''}`,
    },
    { key: 'station', label: 'Station id', render: (row) => row.station_id },
    { key: 'sensor', label: 'Sensor id', render: (row) => row.sensor_id ?? '—' },
    { key: 'observed', label: 'Observed at (UTC)', render: (row) => new Date(row.observation_time).toLocaleString() },
    { key: 'quality', label: 'Quality', render: (row) => <StatusBadge status={row.quality_status} /> },
  ]


  return (
    <div>
      <PageHeader
        title="Latest Monitoring"
        description="Most recent observation stored for each measurement type, with station and timestamp."
        actions={
          <button type="button" className="btn-secondary"
            onClick={() => measurementService.exportFile({ format: 'csv' }, 'emis_measurements.csv')}>
            Export CSV
          </button>
        }
      />

      <div className="card mb-4 flex flex-col gap-3 p-4 sm:flex-row">
        <select className="input sm:w-72" value={stationId} onChange={(event) => setStationId(event.target.value)}>
          <option value="">All stations</option>
          {(stationsQuery.data?.data || []).map((station) => (
            <option key={station.id} value={station.id}>{station.station_code} — {station.name}</option>
          ))}
        </select>
      </div>

      <div className="card overflow-hidden">
        {query.isLoading ? <LoadingSpinner /> : query.isError ? (
          <ErrorState message={extractError(query.error)} onRetry={query.refetch} />
        ) : (
          <DataTable rows={query.data || []} columns={columns} emptyMessage="No measurements have been imported yet." />
        )}
      </div>
    </div>
  )
}
