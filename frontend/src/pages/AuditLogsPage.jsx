import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import PageHeader from '../components/ui/PageHeader'
import { extractError } from '../services/api'
import dashboardService from '../services/dashboardService'

export default function AuditLogsPage() {
  const [page, setPage] = useState(1)
  const [module, setModule] = useState('')
  const [action, setAction] = useState('')

  // Change the query key whenever a filter changes so React Query refetches.
  const query = useQuery({
    queryKey: ['audit-logs', { page, module, action }],
    queryFn: () =>
      dashboardService.getAuditLogs({
        page,
        per_page: 15,
        ...(module ? { module } : {}),
        ...(action ? { action } : {}),
      }),
  })

  const envelope = query.data
  const logs = envelope?.data || []
  const meta = envelope?.meta

  return (
    <div>
      <PageHeader
        title="Audit Logs"
        description="Chronological record of important administrative actions."
      />

      <div className="card mb-4 flex flex-col gap-3 p-4 sm:flex-row">
        <div className="flex-1">
          <label className="label" htmlFor="module">Module</label>
          <input
            id="module"
            className="input"
            placeholder="e.g. auth, stations"
            value={module}
            onChange={(event) => { setModule(event.target.value); setPage(1) }}
          />
        </div>
        <div className="flex-1">
          <label className="label" htmlFor="action">Action</label>
          <input
            id="action"
            className="input"
            placeholder="e.g. LOGIN"
            value={action}
            onChange={(event) => { setAction(event.target.value); setPage(1) }}
          />
        </div>
      </div>

      {query.isLoading ? (
        <LoadingSpinner />
      ) : query.isError ? (
        <ErrorState message={extractError(query.error)} onRetry={query.refetch} />
      ) : logs.length === 0 ? (
        <EmptyState title="No audit entries" description="Actions will appear here as you use the system." />
      ) : (
        <div className="card overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">When</th>
                <th className="px-4 py-2">User</th>
                <th className="px-4 py-2">Action</th>
                <th className="px-4 py-2">Module</th>
                <th className="px-4 py-2">Record</th>
                <th className="px-4 py-2">IP address</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-50">
                  <td className="whitespace-nowrap px-4 py-2 text-slate-600">
                    {new Date(log.occurred_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-2">{log.user_id ?? '—'}</td>
                  <td className="px-4 py-2 font-medium text-slate-800">{log.action}</td>
                  <td className="px-4 py-2">{log.module}</td>
                  <td className="px-4 py-2">{log.record_identifier || '—'}</td>
                  <td className="px-4 py-2">{log.ip_address || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {meta && (
            <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-xs text-slate-600">
              <span>
                Page {meta.page} of {meta.total_pages || 1} · {meta.total} entries
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="btn-secondary disabled:opacity-40"
                  disabled={!meta.has_prev}
                  onClick={() => setPage((value) => value - 1)}
                >
                  Previous
                </button>
                <button
                  type="button"
                  className="btn-secondary disabled:opacity-40"
                  disabled={!meta.has_next}
                  onClick={() => setPage((value) => value + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
