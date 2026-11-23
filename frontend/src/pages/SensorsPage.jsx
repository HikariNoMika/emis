import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import SensorForm from '../components/forms/SensorForm'
import DataTable from '../components/ui/DataTable'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import Modal from '../components/ui/Modal'
import PageHeader from '../components/ui/PageHeader'
import Pagination from '../components/ui/Pagination'
import StatusBadge from '../components/ui/StatusBadge'
import { useStations } from '../hooks/useStations'
import { useSensors } from '../hooks/useSensors'
import { extractError } from '../services/api'
import sensorService from '../services/sensorService'

const STATUSES = ['ACTIVE', 'INACTIVE', 'FAULTY', 'MAINTENANCE', 'UNKNOWN']

export default function SensorsPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [stationId, setStationId] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const [formSensor, setFormSensor] = useState(null)
  const [notice, setNotice] = useState('')

  const params = {
    page, per_page: 15,
    ...(search ? { search } : {}),
    ...(stationId ? { station_id: stationId } : {}),
    ...(status ? { status } : {}),
  }
  const query = useSensors(params)
  const stationsQuery = useStations({ page: 1, per_page: 100 })

  const mutation = useMutation({
    mutationFn: ({ id, payload }) =>
      id ? sensorService.update(id, payload) : sensorService.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sensors'] })
      queryClient.invalidateQueries({ queryKey: ['stations'] })
      setFormSensor(null)
      setNotice('Sensor saved.')
    },
  })

  const columns = [
    { key: 'port', label: 'Port', render: (row) => row.port_number || '—' },
    {
      key: 'name', label: 'Sensor',
      render: (row) => (
        <div>
          <p className="font-medium text-slate-800">{row.name}</p>
          <p className="text-xs text-slate-500">{row.model || '—'} · {row.serial_number || 'no serial'}</p>
        </div>
      ),
    },
    { key: 'station', label: 'Station', render: (row) => row.station_name || '—' },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.operational_status} /> },
    {
      key: 'types', label: 'Measurement types',
      render: (row) => row.measurement_types?.length
        ? row.measurement_types.map((item) => item.code).join(', ')
        : 'Not configured',
    },
    {
      key: 'actions', label: 'Actions',
      render: (row) => (
        <div className="flex gap-2">
          <button type="button" className="text-xs font-medium text-brand-600 hover:underline"
            onClick={() => setFormSensor(row)}>Edit</button>
          <Link to={`/sensors/${row.id}`} className="text-xs font-medium text-brand-600 hover:underline">Health</Link>
        </div>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Sensor Management"
        description="Register equipment and declare which measurement types each sensor produces."
        actions={<button type="button" className="btn-primary" onClick={() => setFormSensor({})}> + Add sensor</button>}
      />

      {notice && <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-800">{notice}</div>}

      <div className="card mb-4 flex flex-col gap-3 p-4 sm:flex-row">
        <input className="input flex-1" placeholder="Search name, model, serial or port…"
          value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} />
        <select className="input sm:w-56" value={stationId}
          onChange={(event) => { setStationId(event.target.value); setPage(1) }}>
          <option value="">All stations</option>
          {(stationsQuery.data?.data || []).map((station) => (
            <option key={station.id} value={station.id}>{station.station_code} — {station.name}</option>
          ))}
        </select>
        <select className="input sm:w-44" value={status}
          onChange={(event) => { setStatus(event.target.value); setPage(1) }}>
          <option value="">All statuses</option>
          {STATUSES.map((item) => <option key={item}>{item}</option>)}
        </select>
      </div>

      <div className="card overflow-hidden">
        {query.isLoading ? <LoadingSpinner /> : query.isError ? (
          <ErrorState message={extractError(query.error)} onRetry={query.refetch} />
        ) : (
          <>
            <DataTable rows={query.data?.data || []} columns={columns} emptyMessage="No sensors found." />
            <Pagination meta={query.data?.meta} onPageChange={setPage} />
          </>
        )}
      </div>

      {formSensor && (
        <Modal title={formSensor.id ? 'Edit sensor' : 'Add sensor'} wide onClose={() => setFormSensor(null)}>
          <SensorForm
            sensor={formSensor.id ? formSensor : null}
            stations={stationsQuery.data?.data || []}
            defaultStationId={stationId ? Number(stationId) : undefined}
            onSubmit={(payload) => mutation.mutateAsync({ id: formSensor.id, payload })}
            onCancel={() => setFormSensor(null)}
            isWorking={mutation.isPending}
          />
          {mutation.isError && <p className="mt-2 text-sm text-red-600">{extractError(mutation.error)}</p>}
        </Modal>
      )}
    </div>
  )
}
