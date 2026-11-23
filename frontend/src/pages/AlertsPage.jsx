import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import DataTable from '../components/ui/DataTable'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import Modal from '../components/ui/Modal'
import PageHeader from '../components/ui/PageHeader'
import Pagination from '../components/ui/Pagination'
import StatusBadge from '../components/ui/StatusBadge'
import { useAlerts } from '../hooks/useMonitoring'
import { extractError } from '../services/api'
import { alertService } from '../services/monitoringService'

export default function AlertsPage() {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState('ACTIVE')
  const [severity, setSeverity] = useState('')
  const [category, setCategory] = useState('')
  const [page, setPage] = useState(1)
  const [action, setAction] = useState(null)
  const [remarks, setRemarks] = useState('')
  const [notice, setNotice] = useState('')

  const query = useAlerts({
    page, per_page: 15,
    ...(status ? { status } : {}),
    ...(severity ? { severity } : {}),
    ...(category ? { category } : {}),
  })

  const mutation = useMutation({
    mutationFn: ({ id, kind, text }) =>
      kind === 'acknowledge' ? alertService.acknowledge(id, text) : alertService.resolve(id, text),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setAction(null)
      setNotice('Alert updated.')
    },
  })

  const columns = [
    { key: 'number', label: 'Alert', render: (row) => <span className="font-medium">{row.alert_number}</span> },
    { key: 'title', label: 'Title', render: (row) => row.title },
    { key: 'category', label: 'Category', render: (row) => row.category },
    { key: 'severity', label: 'Severity', render: (row) => <StatusBadge status={row.severity} /> },
    { key: 'station', label: 'Station id', render: (row) => row.station_id ?? '—' },
    { key: 'last_seen', label: 'Last seen', render: (row) => new Date(row.last_seen_at).toLocaleString() },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
    {
      key: 'actions', label: 'Actions',
      render: (row) => (
        <div className="flex gap-2">
          {row.status === 'ACTIVE' && (
            <button type="button" className="text-xs font-medium text-brand-600 hover:underline"
              onClick={() => { setAction({ alert: row, kind: 'acknowledge' }); setRemarks('') }}>Acknowledge</button>
          )}
          {row.status !== 'RESOLVED' && (
            <button type="button" className="text-xs font-medium text-green-700 hover:underline"
              onClick={() => { setAction({ alert: row, kind: 'resolve' }); setRemarks('') }}>Resolve</button>
          )}
        </div>
      ),
    },
  ]

  return (
    <div>
      <PageHeader title="Alerts" description="Active and historical environmental, equipment and data alerts." />

      {notice && <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-800">{notice}</div>}

      <div className="card mb-4 flex flex-col gap-3 p-4 sm:flex-row">
        <select className="input" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }}>
          <option value="">All statuses</option>
          <option>ACTIVE</option><option>ACKNOWLEDGED</option><option>RESOLVED</option>
        </select>
        <select className="input" value={severity} onChange={(event) => { setSeverity(event.target.value); setPage(1) }}>
          <option value="">All severities</option>
          <option>INFO</option><option>WARNING</option><option>CRITICAL</option>
        </select>
        <select className="input" value={category} onChange={(event) => { setCategory(event.target.value); setPage(1) }}>
          <option value="">All categories</option>
          {['ENVIRONMENTAL', 'EQUIPMENT', 'BATTERY', 'COMMUNICATION', 'MISSING_DATA', 'DATA_QUALITY', 'CALIBRATION', 'MAINTENANCE'].map((item) => <option key={item}>{item}</option>)}
        </select>
      </div>

      <div className="card overflow-hidden">
        {query.isLoading ? <LoadingSpinner /> : query.isError ? (
          <ErrorState message={extractError(query.error)} onRetry={query.refetch} />
        ) : (
          <>
            <DataTable rows={query.data?.data || []} columns={columns} emptyMessage="No alerts match your filters." />
            <Pagination meta={query.data?.meta} onPageChange={setPage} />
          </>
        )}
      </div>

      {action && (
        <Modal
          title={action.kind === 'acknowledge' ? 'Acknowledge alert' : 'Resolve alert'}
          description={action.alert.message}
          onClose={() => setAction(null)}
          footer={
            <>
              <button type="button" className="btn-secondary" onClick={() => setAction(null)}>Cancel</button>
              <button type="button" className="btn-primary" disabled={mutation.isPending}
                onClick={() => mutation.mutateAsync({ id: action.alert.id, kind: action.kind, text: remarks })}>
                {mutation.isPending ? 'Saving…' : action.kind === 'acknowledge' ? 'Acknowledge' : 'Resolve'}
              </button>
            </>
          }
        >
          <label className="label">Remarks</label>
          <textarea className="input" rows="3" value={remarks} onChange={(event) => setRemarks(event.target.value)} />
          {mutation.isError && <p className="mt-2 text-sm text-red-600">{extractError(mutation.error)}</p>}
        </Modal>
      )}
    </div>
  )
}
