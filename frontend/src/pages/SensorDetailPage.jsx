import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import DataTable from '../components/ui/DataTable'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import PageHeader from '../components/ui/PageHeader'
import StatusBadge from '../components/ui/StatusBadge'
import {
  useSensor,
  useSensorHealth,
  useSensorMeasurements,
} from '../hooks/useSensors'
import { extractError } from '../services/api'

export default function SensorDetailPage() {
  const { id } = useParams()
  const sensorId = Number(id)
  const [page, setPage] = useState(1)

  const sensorQuery = useSensor(sensorId)
  const healthQuery = useSensorHealth(sensorId)
  const measurementsQuery = useSensorMeasurements(sensorId, { page, per_page: 20 })

  if (sensorQuery.isLoading || healthQuery.isLoading) return <LoadingSpinner label="Loading sensor…" />
  if (sensorQuery.isError) return <ErrorState message={extractError(sensorQuery.error)} onRetry={sensorQuery.refetch} />
  if (healthQuery.isError) return <ErrorState message={extractError(healthQuery.error)} onRetry={healthQuery.refetch} />

  const sensor = sensorQuery.data
  const health = healthQuery.data

  const columns = [
    { key: 'observation_time', label: 'Observed at', render: (row) => new Date(row.observation_time).toLocaleString() },
    { key: 'type_id', label: 'Type id', render: (row) => row.measurement_type_id },
    { key: 'value', label: 'Value', render: (row) => `${row.normalized_value ?? row.original_value ?? '—'} ${row.unit || ''}` },
    { key: 'quality', label: 'Quality', render: (row) => <StatusBadge status={row.quality_status} /> },
  ]

  return (
    <div>
      <PageHeader
        title={sensor.name}
        description={`Port ${sensor.port_number || '—'} · ${sensor.model || 'No model'} · ${sensor.manufacturer || 'No manufacturer'}`}
        actions={<Link to={`/stations/${sensor.station_id}`} className="btn-secondary">Back to station</Link>}
      />

      <div className="card mb-6 grid grid-cols-2 gap-4 p-4 text-sm sm:grid-cols-4">
        <div><p className="text-xs uppercase text-slate-500">Status</p><StatusBadge status={sensor.operational_status} /></div>
        <div><p className="text-xs uppercase text-slate-500">Serial</p><p>{sensor.serial_number || '—'}</p></div>
        <div><p className="text-xs uppercase text-slate-500">Latest observation</p><p>{health.latest_observation_time ? new Date(health.latest_observation_time).toLocaleString() : '—'}</p></div>
        <div><p className="text-xs uppercase text-slate-500">Data freshness</p><p>{health.data_freshness_minutes ?? '—'} min</p></div>
        <div><p className="text-xs uppercase text-slate-500">Connectivity</p><p>{health.connectivity_state}</p></div>
        <div><p className="text-xs uppercase text-slate-500">Calibration due</p><p>{sensor.next_calibration_date || '—'} {health.calibration_due && <span className="text-red-600">(overdue)</span>}</p></div>
        <div><p className="text-xs uppercase text-slate-500">Measurements</p><p>{health.measurement_count}</p></div>
        <div><p className="text-xs uppercase text-slate-500">Maintenance records</p><p>{health.maintenance_record_count}</p></div>
      </div>

      <div className="card overflow-hidden">
        <div className="border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-900">Recent measurements</h2>
        </div>
        {measurementsQuery.isLoading ? <LoadingSpinner /> : measurementsQuery.isError ? (
          <ErrorState message={extractError(measurementsQuery.error)} onRetry={measurementsQuery.refetch} />
        ) : (
          <div>
            <DataTable rows={measurementsQuery.data?.data || []} columns={columns} emptyMessage="No measurements for this sensor." />
            {measurementsQuery.data?.meta?.total_pages > 1 && (
              <div className="flex justify-end gap-2 border-t border-slate-200 px-4 py-3">
                <button type="button" className="btn-secondary disabled:opacity-40" disabled={page === 1}
                  onClick={() => setPage((value) => value - 1)}>Previous</button>
                <button type="button" className="btn-secondary disabled:opacity-40"
                  disabled={!measurementsQuery.data.meta.has_next}
                  onClick={() => setPage((value) => value + 1)}>Next</button>
              </div>
            )}
          </div>
        )}
      </div>

      <p className="mt-3 text-xs text-slate-500">
        Connectivity is shown as NOT_REPORTED because the system currently receives data through file
        uploads. Late data does not by itself mean equipment is offline.
      </p>
    </div>
  )
}
