import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import DataTable from '../components/ui/DataTable'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import Modal from '../components/ui/Modal'
import PageHeader from '../components/ui/PageHeader'
import Pagination from '../components/ui/Pagination'
import StatusBadge from '../components/ui/StatusBadge'
import SummaryCard from '../components/ui/SummaryCard'
import { useQualityFlags, useQualitySummary } from '../hooks/useMonitoring'
import { extractError } from '../services/api'
import { dataQualityService } from '../services/monitoringService'

const STATUSES = ['VALID', 'SUSPECT', 'INVALID', 'MISSING', 'UNVERIFIED']
const RESOLUTIONS = ['OPEN', 'RESOLVED', 'IGNORED']

export default function DataQualityPage() {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState('')
  const [severity, setSeverity] = useState('')
  const [resolution, setResolution] = useState('OPEN')
  const [page, setPage] = useState(1)
  const [target, setTarget] = useState(null)
  const [resolutionStatus, setResolutionStatus] = useState('RESOLVED')
  const [remarks, setRemarks] = useState('')
  const [notice, setNotice] = useState('')

  const summaryQuery = useQualitySummary()
  const flagsQuery = useQualityFlags({
    page, per_page: 15,
    ...(status ? { quality_status: status } : {}),
    ...(severity ? { severity } : {}),
    ...(resolution ? { resolution_status: resolution } : {}),
  })

  const mutation = useMutation({
    mutationFn: ({ id, payload }) => dataQualityService.resolve(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quality'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setTarget(null)
      setNotice('Quality flag updated.')
    },
  })

  const columns = [
    { key: 'rule', label: 'Rule', render: (row) => row.rule_code },
    { key: 'station', label: 'Station id', render: (row) => row.station_id },
    { key: 'type', label: 'Type id', render: (row) => row.measurement_type_id ?? '—' },
    { key: 'time', label: 'Observed at', render: (row) => row.observation_time ? new Date(row.observation_time).toLocaleString() : '—' },
    { key: 'value', label: 'Original value', render: (row) => `${row.original_value ?? '—'} ${row.unit || ''}` },
    { key: 'quality', label: 'Quality', render: (row) => <StatusBadge status={row.quality_status} /> },
    { key: 'severity', label: 'Severity', render: (row) => <StatusBadge status={row.severity} /> },
    { key: 'explanation', label: 'Explanation', render: (row) => <span className="text-xs text-slate-600">{row.explanation || '—'}</span> },
    {
      key: 'actions', label: 'Actions',
      render: (row) => (
        <button type="button" className="text-xs font-medium text-brand-600 hover:underline"
          onClick={() => { setTarget(row); setResolutionStatus('RESOLVED'); setRemarks(row.admin_remarks || '') }}>
          Resolve
        </button>
      ),
    },
  ]

  const summary = summaryQuery.data

  return (
    <div>
      <PageHeader
        title="Data Quality"
        description="Automated findings. Flagged measurements are kept unchanged; only the flag is resolved."
      />

      {notice && <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-800">{notice}</div>}

      <section className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <SummaryCard label="Total flags" value={summary?.total_flags ?? '—'} />
        <SummaryCard label="Open" value={summary?.open_flags ?? '—'} tone="amber" />
        <SummaryCard label="SUSPECT" value={summary?.by_status?.SUSPECT ?? 0} tone="amber" />
        <SummaryCard label="INVALID" value={summary?.by_status?.INVALID ?? 0} tone="red" />
      </section>

      <div className="card mb-4 flex flex-col gap-3 p-4 sm:flex-row">
        <select className="input" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }}>
          <option value="">All quality statuses</option>
          {STATUSES.map((item) => <option key={item}>{item}</option>)}
        </select>
        <select className="input" value={severity} onChange={(event) => { setSeverity(event.target.value); setPage(1) }}>
          <option value="">All severities</option>
          <option>INFO</option><option>WARNING</option><option>CRITICAL</option>
        </select>
        <select className="input" value={resolution} onChange={(event) => { setResolution(event.target.value); setPage(1) }}>
          <option value="">All resolutions</option>
          {RESOLUTIONS.map((item) => <option key={item}>{item}</option>)}
        </select>
      </div>

      <div className="card overflow-hidden">
        {flagsQuery.isLoading ? <LoadingSpinner /> : flagsQuery.isError ? (
          <ErrorState message={extractError(flagsQuery.error)} onRetry={flagsQuery.refetch} />
        ) : (
          <>
            <DataTable rows={flagsQuery.data?.data || []} columns={columns} emptyMessage="No quality flags match your filters." />
            <Pagination meta={flagsQuery.data?.meta} onPageChange={setPage} />
          </>
        )}
      </div>

      {target && (
        <Modal
          title="Resolve quality flag"
          description={target.explanation}
          onClose={() => setTarget(null)}
          footer={
            <>
              <button type="button" className="btn-secondary" onClick={() => setTarget(null)}>Cancel</button>
              <button type="button" className="btn-primary" disabled={mutation.isPending}
                onClick={() => mutation.mutateAsync({
                  id: target.id,
                  payload: { resolution_status: resolutionStatus, admin_remarks: remarks },
                })}>
                {mutation.isPending ? 'Saving…' : 'Save resolution'}
              </button>
            </>
          }
        >
          <div className="space-y-4">
            <div>
              <label className="label">Resolution</label>
              <select className="input" value={resolutionStatus} onChange={(event) => setResolutionStatus(event.target.value)}>
                {RESOLUTIONS.map((item) => <option key={item}>{item}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Administrator remarks</label>
              <textarea className="input" rows="4" value={remarks} onChange={(event) => setRemarks(event.target.value)} />
            </div>
            <p className="text-xs text-slate-500">The original measurement value is never changed by this action.</p>
            {mutation.isError && <p className="text-sm text-red-600">{extractError(mutation.error)}</p>}
          </div>
        </Modal>
      )}
    </div>
  )
}
