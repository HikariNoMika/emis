import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import SensorForm from '../components/forms/SensorForm'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import DataTable from '../components/ui/DataTable'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import Modal from '../components/ui/Modal'
import PageHeader from '../components/ui/PageHeader'
import StatusBadge from '../components/ui/StatusBadge'
import { useMeasurementTypes } from '../hooks/useSensors'
import { useStation, useStationRelated } from '../hooks/useStations'
import { extractError } from '../services/api'
import importService from '../services/importService'
import sensorService from '../services/sensorService'
import stationService from '../services/stationService'

const TABS = [
  { key: 'sensors', label: 'Sensors' },
  { key: 'measurements', label: 'Measurements' },
  { key: 'status', label: 'Status history' },
  { key: 'maintenance', label: 'Maintenance' },
  { key: 'imports', label: 'Imports' },
  { key: 'history', label: 'Change history' },
]

export default function StationDetailPage() {
  const { id } = useParams()
  const stationId = Number(id)
  const queryClient = useQueryClient()
  const [tab, setTab] = useState('sensors')
  const [sensorFormOpen, setSensorFormOpen] = useState(false)
  const [editingSensor, setEditingSensor] = useState(null)
  const [archiveSensor, setArchiveSensor] = useState(null)
  const [typeSensor, setTypeSensor] = useState(null)
  const [selectedTypes, setSelectedTypes] = useState([])
  const [columnHints, setColumnHints] = useState({})
  const [renameOpen, setRenameOpen] = useState(false)
  const [renameValue, setRenameValue] = useState('')
  const [importFile, setImportFile] = useState(null)
  const [importSheet, setImportSheet] = useState('')
  const [pendingBatch, setPendingBatch] = useState(null)
  const [notice, setNotice] = useState('')

  const stationQuery = useStation(stationId)
  const relatedQuery = useStationRelated(stationId, tab)
  const typesQuery = useMeasurementTypes()

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['stations', stationId] })
    queryClient.invalidateQueries({ queryKey: ['stations', stationId, tab] })
    queryClient.invalidateQueries({ queryKey: ['sensors'] })
  }

  const renameMutation = useMutation({
    mutationFn: (name) => stationService.update(stationId, { name }),
    onSuccess: () => {
      invalidate()
      setRenameOpen(false)
      setNotice('Station renamed.')
    },
  })

  const uploadImportMutation = useMutation({
    mutationFn: (formData) => importService.upload(formData),
    onSuccess: (batch) => {
      setPendingBatch(batch)
      setNotice('File inspected. Review the details below, then process it.')
      queryClient.invalidateQueries({ queryKey: ['imports'] })
    },
  })

  const processImportMutation = useMutation({
    mutationFn: (batchId) => importService.process(batchId),
    onSuccess: (result) => {
      const summary = result?.summary || {}
      setPendingBatch(null)
      setImportFile(null)
      invalidate()
      queryClient.invalidateQueries({ queryKey: ['imports'] })
      setNotice(
        `Import complete: ${summary.imported_rows ?? 0} new readings, ` +
        `${summary.duplicate_rows ?? 0} duplicates skipped.`,
      )
    },
  })

  const sensorMutation = useMutation({
    mutationFn: ({ sensorId, payload }) =>
      sensorId ? sensorService.update(sensorId, payload) : sensorService.create(payload),
    onSuccess: () => {
      invalidate()
      setSensorFormOpen(false)
      setEditingSensor(null)
      setNotice('Sensor saved.')
    },
  })

  const archiveSensorMutation = useMutation({
    mutationFn: (sensor) => sensorService.update(sensor.id, { is_archived: true }),
    onSuccess: () => {
      invalidate()
      setArchiveSensor(null)
      setNotice('Sensor archived.')
    },
  })

  const typeMutation = useMutation({
    mutationFn: () =>
      sensorService.setMeasurementTypes(typeSensor.id, {
        measurement_type_ids: selectedTypes,
        column_hints: columnHints,
      }),
    onSuccess: () => {
      invalidate()
      setTypeSensor(null)
      setNotice('Measurement types updated.')
    },
  })

  const openTypeModal = (sensor) => {
    setTypeSensor(sensor)
    const current = sensor.measurement_types || []
    setSelectedTypes(current.map((item) => item.id))
    setColumnHints(
      current.reduce((acc, item) => {
        if (item.column_hint) acc[String(item.id)] = item.column_hint
        return acc
      }, {}),
    )
  }

  if (stationQuery.isLoading) return <LoadingSpinner label="Loading station…" />
  if (stationQuery.isError) {
    return <ErrorState message={extractError(stationQuery.error)} onRetry={stationQuery.refetch} />
  }

  const station = stationQuery.data
  const rows = relatedQuery.data?.data || []

  const sensorColumns = [
    { key: 'port_number', label: 'Port', render: (row) => row.port_number || '—' },
    {
      key: 'name',
      label: 'Sensor',
      render: (row) => (
        <div>
          <p className="font-medium text-slate-800">{row.name}</p>
          <p className="text-xs text-slate-500">{row.model || '—'} · {row.manufacturer || '—'}</p>
        </div>
      ),
    },
    { key: 'serial_number', label: 'Serial', render: (row) => row.serial_number || '—' },
    { key: 'operational_status', label: 'Status', render: (row) => <StatusBadge status={row.operational_status} /> },
    {
      key: 'measurement_types',
      label: 'Produces',
      render: (row) => row.measurement_types?.map((item) => item.code).join(', ') || 'Not configured',
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (row) => (
        <div className="flex flex-wrap gap-2">
          <button type="button" className="text-xs font-medium text-brand-600 hover:underline"
            onClick={() => { setEditingSensor(row); setSensorFormOpen(true) }}>Edit</button>
          <button type="button" className="text-xs font-medium text-brand-600 hover:underline"
            onClick={() => openTypeModal(row)}>Measurement types</button>
          <Link to={`/sensors/${row.id}`} className="text-xs font-medium text-brand-600 hover:underline">Health</Link>
          {!row.is_archived && (
            <button type="button" className="text-xs font-medium text-red-600 hover:underline"
              onClick={() => setArchiveSensor(row)}>Archive</button>
          )}
        </div>
      ),
    },
  ]

  const measurementColumns = [
    { key: 'observation_time', label: 'Observed at', render: (row) => new Date(row.observation_time).toLocaleString() },
    { key: 'type', label: 'Measurement type id', render: (row) => row.measurement_type_id },
    { key: 'value', label: 'Value', render: (row) => `${row.normalized_value ?? row.original_value ?? '—'} ${row.unit || ''}` },
    { key: 'quality', label: 'Quality', render: (row) => <StatusBadge status={row.quality_status} /> },
  ]

  const statusColumns = [
    { key: 'recorded_at', label: 'Recorded at', render: (row) => new Date(row.recorded_at).toLocaleString() },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
    { key: 'freshness', label: 'Freshness (min)', render: (row) => row.data_freshness_minutes ?? '—' },
    { key: 'battery', label: 'Battery %', render: (row) => row.battery_percentage ?? '—' },
    { key: 'last_observation_time', label: 'Last observation', render: (row) => row.last_observation_time ? new Date(row.last_observation_time).toLocaleString() : '—' },
  ]

  const maintenanceColumns = [
    { key: 'maintenance_date', label: 'Date', render: (row) => row.maintenance_date },
    { key: 'maintenance_type', label: 'Type', render: (row) => row.maintenance_type },
    { key: 'performed_by', label: 'Performed by', render: (row) => row.performed_by || '—' },
    { key: 'description', label: 'Description', render: (row) => row.description || '—' },
  ]

  const importColumns = [
    { key: 'batch_number', label: 'Batch', render: (row) => row.batch_number },
    { key: 'original_filename', label: 'File', render: (row) => row.original_filename },
    { key: 'status', label: 'Status', render: (row) => row.status },
    { key: 'imported_rows', label: 'Imported rows', render: (row) => row.imported_rows },
  ]

  const historyColumns = [
    { key: 'occurred_at', label: 'When', render: (row) => new Date(row.occurred_at).toLocaleString() },
    { key: 'action', label: 'Action', render: (row) => row.action },
    { key: 'record_identifier', label: 'Record', render: (row) => row.record_identifier || '—' },
  ]

  let columns = sensorColumns
  if (tab === 'measurements') columns = measurementColumns
  if (tab === 'status') columns = statusColumns
  if (tab === 'maintenance') columns = maintenanceColumns
  if (tab === 'imports') columns = importColumns
  if (tab === 'history') columns = historyColumns

  return (
    <div>
      <PageHeader
        title={`${station.name} (${station.station_code})`}
        description={station.site_name || 'Station details and associated records'}
        actions={
          <>
            <Link to="/map" className="btn-secondary">View on map</Link>
            <button type="button" className="btn-secondary"
              onClick={() => { setRenameValue(station.name); setRenameOpen(true) }}>
              Rename
            </button>
            <button type="button" className="btn-primary" onClick={() => { setEditingSensor(null); setSensorFormOpen(true) }}>
              + Add sensor
            </button>
          </>
        }
      />

      {notice && <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-800">{notice}</div>}

      {/* Per-station Excel / CSV import */}
      <section className="card mb-6 p-4">
        <div className="mb-3">
          <h2 className="text-sm font-semibold text-slate-900">Import monitoring data</h2>
          <p className="text-xs text-slate-500">
            Upload an Excel or CSV export for <strong>{station.name}</strong>. Existing readings are never overwritten.
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label className="label" htmlFor="station-import-file">Excel (.xlsx) or CSV file</label>
            <input id="station-import-file" type="file" accept=".xlsx,.xlsm,.csv"
              className="input" onChange={(event) => setImportFile(event.target.files?.[0] || null)} />
          </div>
          <div className="sm:w-56">
            <label className="label" htmlFor="station-import-sheet">Worksheet (optional)</label>
            <input id="station-import-sheet" className="input" placeholder="e.g. Config 1"
              value={importSheet} onChange={(event) => setImportSheet(event.target.value)} />
          </div>
          <button type="button" className="btn-primary" disabled={!importFile || uploadImportMutation.isPending}
            onClick={() => {
              const formData = new FormData()
              formData.append('file', importFile)
              formData.append('station_id', String(stationId))
              if (importSheet.trim()) formData.append('sheet_name', importSheet.trim())
              uploadImportMutation.mutate(formData)
            }}>
            {uploadImportMutation.isPending ? 'Inspecting…' : 'Upload & inspect'}
          </button>
        </div>
        {uploadImportMutation.isError && (
          <p className="mt-2 text-sm text-red-600">{extractError(uploadImportMutation.error)}</p>
        )}

        {pendingBatch && (
          <div className="mt-4 rounded-md border border-brand-200 bg-brand-50 p-3 text-sm">
            <p><strong>{pendingBatch.original_filename}</strong></p>
            <p>Sheets: {(pendingBatch.sheet_names || []).join(', ') || '—'}</p>
            <p>Rows found: {pendingBatch.total_rows}</p>
            {pendingBatch.warnings?.length > 0 && (
              <p className="text-amber-700">{pendingBatch.warnings.length} warning(s) — review in Data Management.</p>
            )}
            <div className="mt-3 flex gap-2">
              <button type="button" className="btn-primary" disabled={processImportMutation.isPending}
                onClick={() => processImportMutation.mutate(pendingBatch.id)}>
                {processImportMutation.isPending ? 'Processing…' : 'Process import'}
              </button>
              <button type="button" className="btn-secondary" onClick={() => setPendingBatch(null)}>Cancel</button>
            </div>
            {processImportMutation.isError && (
              <p className="mt-2 text-sm text-red-600">{extractError(processImportMutation.error)}</p>
            )}
          </div>
        )}
      </section>

      <div className="card mb-6 grid grid-cols-2 gap-4 p-4 text-sm sm:grid-cols-4">
        <div><p className="text-xs uppercase text-slate-500">Status</p><StatusBadge status={station.operational_status} /></div>
        <div><p className="text-xs uppercase text-slate-500">Device serial</p><p>{station.device_serial_number || '—'}</p></div>
        <div><p className="text-xs uppercase text-slate-500">Coordinates</p><p>{station.latitude != null ? `${station.latitude}, ${station.longitude}` : '—'}</p></div>
        <div><p className="text-xs uppercase text-slate-500">Interval</p><p>{station.measurement_interval_seconds}s</p></div>
        <div><p className="text-xs uppercase text-slate-500">Sensors</p><p>{station.sensor_count ?? '—'}</p></div>
        <div><p className="text-xs uppercase text-slate-500">Measurements</p><p>{station.measurement_count ?? '—'}</p></div>
        <div><p className="text-xs uppercase text-slate-500">Imports</p><p>{station.import_count ?? '—'}</p></div>
        <div><p className="text-xs uppercase text-slate-500">Timezone</p><p>{station.timezone}</p></div>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        {TABS.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setTab(item.key)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${
              tab === item.key ? 'bg-brand-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-100'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="card overflow-hidden">
        {relatedQuery.isLoading ? (
          <LoadingSpinner />
        ) : relatedQuery.isError ? (
          <ErrorState message={extractError(relatedQuery.error)} onRetry={relatedQuery.refetch} />
        ) : rows.length === 0 ? (
          <div className="p-4"><EmptyState title={`No ${tab} records`} /></div>
        ) : (
          <DataTable rows={rows} columns={columns} keyField="id" />
        )}
      </div>

      {sensorFormOpen && (
        <Modal
          title={editingSensor ? 'Edit sensor' : 'Add sensor'}
          description="One sensor may produce several measurement types; configure those separately."
          wide
          onClose={() => setSensorFormOpen(false)}
        >
          <SensorForm
            sensor={editingSensor}
            defaultStationId={stationId}
            stations={[station]}
            onSubmit={(payload) => sensorMutation.mutateAsync({ sensorId: editingSensor?.id, payload })}
            onCancel={() => setSensorFormOpen(false)}
            isWorking={sensorMutation.isPending}
          />
          {sensorMutation.isError && <p className="mt-2 text-sm text-red-600">{extractError(sensorMutation.error)}</p>}
        </Modal>
      )}

      {archiveSensor && (
        <ConfirmDialog
          title="Archive sensor?"
          message={`Archive "${archiveSensor.name}"? Its historical measurements remain in the database.`}
          confirmLabel="Archive sensor"
          isWorking={archiveSensorMutation.isPending}
          onCancel={() => setArchiveSensor(null)}
          onConfirm={() => archiveSensorMutation.mutate(archiveSensor)}
        />
      )}

      {typeSensor && (
        <Modal
          title="Measurement types"
          description={`Select what "${typeSensor.name}" reports. Column hints help the importer map future files.`}
          onClose={() => setTypeSensor(null)}
          footer={
            <>
              <button type="button" className="btn-secondary" onClick={() => setTypeSensor(null)}>Cancel</button>
              <button type="button" className="btn-primary" disabled={typeMutation.isPending}
                onClick={() => typeMutation.mutate()}>
                {typeMutation.isPending ? 'Saving…' : 'Save types'}
              </button>
            </>
          }
        >
          {typesQuery.isLoading ? <LoadingSpinner /> : (
            <div className="space-y-2">
              {(typesQuery.data || []).map((type) => (
                <div key={type.id} className="rounded border border-slate-200 p-2">
                  <label className="flex items-center gap-2 text-sm text-slate-800">
                    <input
                      type="checkbox"
                      checked={selectedTypes.includes(type.id)}
                      onChange={(event) => {
                        setSelectedTypes((current) =>
                          event.target.checked
                            ? [...current, type.id]
                            : current.filter((item) => item !== type.id),
                        )
                      }}
                    />
                    {type.name} <span className="text-xs text-slate-500">({type.unit})</span>
                  </label>
                  {selectedTypes.includes(type.id) && (
                    <input
                      className="input mt-2 text-xs"
                      placeholder="Original spreadsheet column name (optional)"
                      value={columnHints[String(type.id)] || ''}
                      onChange={(event) =>
                        setColumnHints((current) => ({ ...current, [String(type.id)]: event.target.value }))
                      }
                    />
                  )}
                </div>
              ))}
            </div>
          )}
          {typeMutation.isError && <p className="mt-2 text-sm text-red-600">{extractError(typeMutation.error)}</p>}
        </Modal>
      )}

      {renameOpen && (
        <Modal
          title="Rename station"
          description="The station code and historical data stay unchanged."
          onClose={() => setRenameOpen(false)}
          footer={<>
            <button type="button" className="btn-secondary" onClick={() => setRenameOpen(false)}>Cancel</button>
            <button type="button" className="btn-primary" disabled={!renameValue.trim() || renameMutation.isPending}
              onClick={() => renameMutation.mutate(renameValue.trim())}>
              {renameMutation.isPending ? 'Saving…' : 'Save name'}
            </button>
          </>}
        >
          <label className="label" htmlFor="rename-input">Station name</label>
          <input id="rename-input" className="input" value={renameValue}
            onChange={(event) => setRenameValue(event.target.value)} />
          <p className="mt-2 text-xs text-slate-500">Station code: {station.station_code}</p>
          {renameMutation.isError && (
            <p className="mt-2 text-sm text-red-600">{extractError(renameMutation.error)}</p>
          )}
        </Modal>
      )}
    </div>
  )
}
