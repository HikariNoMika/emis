import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import MaintenanceForm from '../components/forms/MaintenanceForm'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import DataTable from '../components/ui/DataTable'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import Modal from '../components/ui/Modal'
import PageHeader from '../components/ui/PageHeader'
import Pagination from '../components/ui/Pagination'
import { useMaintenance, useMaintenanceCalendar } from '../hooks/useAdministration'
import { useSensors } from '../hooks/useSensors'
import { useStations } from '../hooks/useStations'
import { extractError } from '../services/api'
import maintenanceService from '../services/maintenanceService'

export default function MaintenancePage() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [deleting, setDeleting] = useState(null)
  const [notice, setNotice] = useState('')

  const query = useMaintenance({ page, per_page: 15 })
  const calendarQuery = useMaintenanceCalendar()
  const stationsQuery = useStations({ page: 1, per_page: 100 })
  const sensorsQuery = useSensors({ per_page: 100 })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['maintenance'] })
    queryClient.invalidateQueries({ queryKey: ['stations'] })
    queryClient.invalidateQueries({ queryKey: ['audit-logs'] })
  }

  const mutation = useMutation({
    mutationFn: ({ id, payload }) =>
      id ? maintenanceService.update(id, payload) : maintenanceService.create(payload),
    onSuccess: () => {
      invalidate(); setFormOpen(false); setEditing(null); setNotice('Maintenance record saved.')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => maintenanceService.remove(id),
    onSuccess: () => { invalidate(); setDeleting(null); setNotice('Maintenance record deleted.') },
  })

  const columns = [
    { key: 'date', label: 'Date', render: (row) => row.maintenance_date },
    { key: 'type', label: 'Type', render: (row) => row.maintenance_type },
    { key: 'station', label: 'Station id', render: (row) => row.station_id },
    { key: 'sensor', label: 'Sensor id', render: (row) => row.sensor_id ?? '—' },
    { key: 'by', label: 'Performed by', render: (row) => row.performed_by || '—' },
    { key: 'next', label: 'Next date', render: (row) => row.next_maintenance_date || '—' },
    { key: 'description', label: 'Description', render: (row) => row.description || '—' },
    {
      key: 'actions', label: 'Actions',
      render: (row) => (
        <div className="flex gap-2">
          <button type="button" className="text-xs font-medium text-brand-600 hover:underline"
            onClick={() => { setEditing(row); setFormOpen(true) }}>Edit</button>
          <button type="button" className="text-xs font-medium text-red-600 hover:underline"
            onClick={() => setDeleting(row)}>Delete</button>
        </div>
      ),
    },
  ]

  const calendar = calendarQuery.data

  return (
    <div>
      <PageHeader
        title="Maintenance & Calibration"
        description="Track maintenance visits, calibration work and upcoming service dates."
        actions={<button type="button" className="btn-primary" onClick={() => { setEditing(null); setFormOpen(true) }}> + Add record</button>}
      />

      {notice && <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-800">{notice}</div>}

      <div className="mb-6 grid gap-4 md:grid-cols-2">
        <div className="card p-4">
          <h2 className="mb-2 text-sm font-semibold text-slate-900">Upcoming maintenance</h2>
          {(calendar?.upcoming || []).length === 0 ? <p className="text-sm text-slate-500">Nothing scheduled.</p> : (
            <div className="divide-y divide-slate-100">
              {calendar.upcoming.slice(0, 5).map((item) => (
                <div key={item.id} className="flex justify-between py-2 text-sm">
                  <span>{item.maintenance_type} · station {item.station_id}</span>
                  <span className="text-slate-500">{item.next_maintenance_date}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="card p-4">
          <h2 className="mb-2 text-sm font-semibold text-red-700">Overdue maintenance</h2>
          {(calendar?.overdue || []).length === 0 ? <p className="text-sm text-slate-500">Nothing overdue.</p> : (
            <div className="divide-y divide-slate-100">
              {calendar.overdue.slice(0, 5).map((item) => (
                <div key={item.id} className="flex justify-between py-2 text-sm">
                  <span>{item.maintenance_type} · station {item.station_id}</span>
                  <span className="text-red-600">{item.next_maintenance_date}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="card overflow-hidden">
        {query.isLoading ? <LoadingSpinner /> : query.isError ? (
          <ErrorState message={extractError(query.error)} onRetry={query.refetch} />
        ) : (
          <>
            <DataTable rows={query.data?.data || []} columns={columns} emptyMessage="No maintenance records." />
            <Pagination meta={query.data?.meta} onPageChange={setPage} />
          </>
        )}
      </div>

      {formOpen && (
        <Modal title={editing ? 'Edit maintenance record' : 'Add maintenance record'} wide onClose={() => setFormOpen(false)}>
          <MaintenanceForm
            record={editing}
            stations={stationsQuery.data?.data || []}
            sensors={sensorsQuery.data?.data || []}
            onSubmit={(payload) => mutation.mutateAsync({ id: editing?.id, payload })}
            onCancel={() => setFormOpen(false)}
            isWorking={mutation.isPending}
          />
          {mutation.isError && <p className="mt-2 text-sm text-red-600">{extractError(mutation.error)}</p>}
        </Modal>
      )}

      {deleting && (
        <ConfirmDialog
          title="Delete maintenance record?"
          message="This record will be removed, and the deletion will be written to the audit log."
          confirmLabel="Delete"
          isWorking={deleteMutation.isPending}
          onCancel={() => setDeleting(null)}
          onConfirm={() => deleteMutation.mutate(deleting.id)}
        />
      )}
    </div>
  )
}
