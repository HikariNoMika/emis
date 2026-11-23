import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import DataTable from '../components/ui/DataTable'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import Modal from '../components/ui/Modal'
import PageHeader from '../components/ui/PageHeader'
import Pagination from '../components/ui/Pagination'
import StatusBadge from '../components/ui/StatusBadge'
import StationForm from '../components/forms/StationForm'
import { useStations } from '../hooks/useStations'
import { extractError } from '../services/api'
import stationService from '../services/stationService'

const STATUSES = ['ONLINE', 'DELAYED', 'OFFLINE', 'MAINTENANCE', 'UNKNOWN']

export default function StationsPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [archived, setArchived] = useState(false)
  const [page, setPage] = useState(1)
  const [formStation, setFormStation] = useState(null) // null = closed, {} = new
  const [archiveTarget, setArchiveTarget] = useState(null)
  const [notice, setNotice] = useState('')

  const params = {
    page,
    per_page: 15,
    ...(search ? { search } : {}),
    ...(status ? { status } : {}),
    is_archived: archived,
  }
  const query = useStations(params)

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['stations'] })
    queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  }

  const saveMutation = useMutation({
    mutationFn: ({ id, payload }) =>
      id ? stationService.update(id, payload) : stationService.create(payload),
    onSuccess: () => {
      invalidate()
      setFormStation(null)
      setNotice('Station saved successfully.')
    },
  })

  const archiveMutation = useMutation({
    mutationFn: (id) => stationService.archive(id),
    onSuccess: () => {
      invalidate()
      setArchiveTarget(null)
      setNotice('Station archived. Historical measurements were preserved.')
    },
  })

  const columns = [
    {
      key: 'station_code',
      label: 'Code',
      render: (row) => <span className="font-medium text-slate-800">{row.station_code}</span>,
    },
    {
      key: 'name',
      label: 'Station',
      render: (row) => (
        <div>
          <Link to={`/stations/${row.id}`} className="font-medium text-brand-600 hover:underline">
            {row.name}
          </Link>
          <p className="text-xs text-slate-500">{row.site_name || '—'}</p>
        </div>
      ),
    },
    {
      key: 'location',
      label: 'Coordinates',
      render: (row) =>
        row.latitude != null && row.longitude != null
          ? `${Number(row.latitude).toFixed(4)}, ${Number(row.longitude).toFixed(4)}`
          : 'Not set',
    },
    {
      key: 'device_serial_number',
      label: 'Device serial',
      render: (row) => row.device_serial_number || '—',
    },
    {
      key: 'operational_status',
      label: 'Status',
      render: (row) => <StatusBadge status={row.operational_status} />,
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (row) => (
        <div className="flex gap-2">
          <button
            type="button"
            className="text-xs font-medium text-brand-600 hover:underline"
            onClick={() => setFormStation(row)}
          >
            Edit
          </button>
          {!row.is_archived && (
            <button
              type="button"
              className="text-xs font-medium text-red-600 hover:underline"
              onClick={() => setArchiveTarget(row)}
            >
              Archive
            </button>
          )}
        </div>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Monitoring Stations"
        description="Register and maintain environmental monitoring stations."
        actions={
          <button type="button" className="btn-primary" onClick={() => setFormStation({})}>
            + Add station
          </button>
        }
      />

      {notice && (
        <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-800">
          {notice}
          <button type="button" className="float-right font-semibold" onClick={() => setNotice('')}>×</button>
        </div>
      )}

      <div className="card mb-4 flex flex-col gap-3 p-4 sm:flex-row">
        <input
          className="input flex-1"
          placeholder="Search code, name, site or serial…"
          value={search}
          onChange={(event) => { setSearch(event.target.value); setPage(1) }}
        />
        <select
          className="input sm:w-48"
          value={status}
          onChange={(event) => { setStatus(event.target.value); setPage(1) }}
        >
          <option value="">All statuses</option>
          {STATUSES.map((item) => <option key={item}>{item}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={archived}
            onChange={(event) => { setArchived(event.target.checked); setPage(1) }}
          />
          Show archived
        </label>
      </div>

      <div className="card overflow-hidden">
        {query.isLoading ? (
          <LoadingSpinner />
        ) : query.isError ? (
          <ErrorState message={extractError(query.error)} onRetry={query.refetch} />
        ) : (
          <>
            <DataTable rows={query.data?.data || []} columns={columns} emptyMessage="No stations match your filters." />
            <Pagination meta={query.data?.meta} onPageChange={setPage} />
          </>
        )}
      </div>

      {formStation && (
        <Modal
          title={formStation.id ? 'Edit station' : 'Add station'}
          description="Coordinates are optional, but required for the station map."
          wide
          onClose={() => setFormStation(null)}
        >
          <StationForm
            station={formStation.id ? formStation : null}
            onSubmit={(payload) =>
              saveMutation.mutateAsync({ id: formStation.id, payload })
            }
            onCancel={() => setFormStation(null)}
            isWorking={saveMutation.isPending}
          />
          {saveMutation.isError && (
            <p className="mt-2 text-sm text-red-600">{extractError(saveMutation.error)}</p>
          )}
        </Modal>
      )}

      {archiveTarget && (
        <ConfirmDialog
          title="Archive station?"
          message={`Archiving "${archiveTarget.name}" hides it from active lists. Its measurements and history are preserved and cannot be lost.`}
          confirmLabel="Archive station"
          isWorking={archiveMutation.isPending}
          onConfirm={() => archiveMutation.mutate(archiveTarget.id)}
          onCancel={() => setArchiveTarget(null)}
        />
      )}
    </div>
  )
}
