import { useMutation, useQueryClient } from '@tanstack/react-query'
import DataTable from '../components/ui/DataTable'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import PageHeader from '../components/ui/PageHeader'
import StatusBadge from '../components/ui/StatusBadge'
import { useStationHealth } from '../hooks/useMonitoring'
import { extractError } from '../services/api'
import { healthService } from '../services/monitoringService'

export default function StationHealthPage() {
  const queryClient = useQueryClient()
  const query = useStationHealth()

  const refreshMutation = useMutation({
    mutationFn: () => healthService.refresh(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['health'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['stations'] })
    },
  })

  const columns = [
    { key: 'station', label: 'Station id', render: (row) => row.station_id },
    { key: 'status', label: 'Data status', render: (row) => <StatusBadge status={row.status} /> },
    { key: 'freshness', label: 'Freshness (min)', render: (row) => row.data_freshness_minutes ?? '—' },
    { key: 'last', label: 'Last observation', render: (row) => row.last_observation_time ? new Date(row.last_observation_time).toLocaleString() : '—' },
    { key: 'battery', label: 'Battery %', render: (row) => row.battery_percentage ?? '—' },
    { key: 'connectivity', label: 'Connectivity', render: (row) => row.connectivity_state || 'NOT_REPORTED' },
    { key: 'recorded', label: 'Evaluated at', render: (row) => row.recorded_at ? new Date(row.recorded_at).toLocaleString() : '—' },
  ]

  return (
    <div>
      <PageHeader
        title="Station Health"
        description="Data freshness, battery and connectivity status derived from stored observations."
        actions={
          <button type="button" className="btn-primary" disabled={refreshMutation.isPending}
            onClick={() => refreshMutation.mutate()}>
            {refreshMutation.isPending ? 'Evaluating…' : 'Refresh status'}
          </button>
        }
      />

      {refreshMutation.isError && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {extractError(refreshMutation.error)}
        </div>
      )}

      <div className="card overflow-hidden">
        {query.isLoading ? <LoadingSpinner /> : query.isError ? (
          <ErrorState message={extractError(query.error)} onRetry={query.refetch} />
        ) : (
          <DataTable rows={query.data || []} columns={columns} emptyMessage="No active stations yet." />
        )}
      </div>

      <div className="mt-4 rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
        <strong>Important:</strong> this system currently receives data by file upload. A delayed upload
        means stale data, not necessarily a station that is offline. Physical connectivity is reported
        separately as NOT_REPORTED until device communication data becomes available.
      </div>
    </div>
  )
}
