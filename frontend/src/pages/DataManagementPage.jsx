import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import DataTable from '../components/ui/DataTable'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import ImportProgressBar from '../components/ui/ImportProgressBar'
import Modal from '../components/ui/Modal'
import PageHeader from '../components/ui/PageHeader'
import Pagination from '../components/ui/Pagination'
import StatusBadge from '../components/ui/StatusBadge'
import { useImportPreview, useImportProgress, useImports } from '../hooks/useImports'
import { useMeasurementTypes, useSensors } from '../hooks/useSensors'
import { useStations } from '../hooks/useStations'
import { extractError } from '../services/api'
import importService from '../services/importService'

export default function DataManagementPage() {
  const queryClient = useQueryClient()
  const [file, setFile] = useState(null)
  const [stationId, setStationId] = useState('')
  const [page, setPage] = useState(1)
  const [selectedBatch, setSelectedBatch] = useState(null)
  const [notice, setNotice] = useState('')
  const [draftMapping, setDraftMapping] = useState(null)
  const [activeBatchId, setActiveBatchId] = useState(null)

  const importsQuery = useImports({ page, per_page: 15 })
  const stationsQuery = useStations({ page: 1, per_page: 100 })
  const previewQuery = useImportPreview(selectedBatch?.id)
  const progressQuery = useImportProgress(activeBatchId, Boolean(activeBatchId))
  const typesQuery = useMeasurementTypes()
  const sensorsQuery = useSensors({
    station_id: draftMapping?.station_id || selectedBatch?.station_id,
    per_page: 100,
  })

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['imports'] })
    queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    queryClient.invalidateQueries({ queryKey: ['stations'] })
    queryClient.invalidateQueries({ queryKey: ['measurements'] })
  }

  const uploadMutation = useMutation({
    mutationFn: (formData) => importService.upload(formData),
    onSuccess: (batch) => {
      invalidateAll()
      setFile(null)
      setNotice(`File "${batch.original_filename}" was inspected (${batch.total_rows} rows). Review the mapping below.`)
      setSelectedBatch(batch)
    },
  })

  const mappingMutation = useMutation({
    mutationFn: ({ id, payload }) => importService.updateMapping(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['imports', selectedBatch.id, 'preview'] })
      queryClient.invalidateQueries({ queryKey: ['imports'] })
      setNotice('Mapping saved.')
    },
  })

  const processMutation = useMutation({
    mutationFn: (id) => importService.process(id),
    onSuccess: (result) => {
      invalidateAll()
      setNotice(
        result.queued
          ? 'Large import queued for background processing.'
          : `Import complete: ${result.summary.imported_rows} inserted, ${result.summary.duplicate_rows} duplicates skipped.`,
      )
      setSelectedBatch(null)
      setActiveBatchId(null)
    },
    onError: () => setActiveBatchId(null),
  })

  const handleUpload = (event) => {
    event.preventDefault()
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    if (stationId) formData.append('station_id', stationId)
    uploadMutation.mutate(formData)
  }

  const openPreview = (batch) => {
    setSelectedBatch(batch)
    setDraftMapping(null)
  }

  const preview = previewQuery.data
  const mapping = draftMapping || preview?.mapping || {}
  const headers = preview?.rows?.[0] ? Object.keys(preview.rows[0].raw_payload) : []
  // The real workbook has no single "Port" data column: ports are a banner
  // above the measurement columns. Use the ports recovered from that banner,
  // plus any explicitly mapped port column from other workbooks.
  const portValues = [
    ...new Set([
      ...Object.values(mapping.measurement_ports || {}),
      ...(preview?.rows || []).map((row) => row.port_value).filter((value) => value != null),
    ]),
  ]

  const updateMappingField = (key, value) =>
    setDraftMapping({ ...mapping, [key]: value })

  const saveAndProcess = async () => {
    await mappingMutation.mutateAsync({ id: selectedBatch.id, payload: mapping })
    setActiveBatchId(selectedBatch.id)
    await processMutation.mutateAsync(selectedBatch.id)
  }

  const historyColumns = [
    { key: 'batch_number', label: 'Batch', render: (row) => <span className="font-medium">{row.batch_number}</span> },
    { key: 'file', label: 'File', render: (row) => row.original_filename },
    { key: 'imported_at', label: 'Uploaded', render: (row) => new Date(row.file_imported_at).toLocaleString() },
    { key: 'rows', label: 'Rows', render: (row) => row.total_rows },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status === 'COMPLETED' ? 'RESOLVED' : row.status === 'FAILED' ? 'INVALID' : 'UNVERIFIED'} /> },
    {
      key: 'actions', label: 'Actions',
      render: (row) => (
        <button type="button" className="text-xs font-medium text-brand-600 hover:underline"
          onClick={() => openPreview(row)}>Review</button>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Data Management"
        description="Upload Excel or CSV monitoring files, review detected columns, then confirm the import."
      />

      {notice && (
        <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-800">
          {notice}
          <button type="button" className="float-right font-semibold" onClick={() => setNotice('')}>×</button>
        </div>
      )}

      <div className="card mb-6 p-5">
        <h2 className="mb-4 text-sm font-semibold text-slate-900">Upload monitoring file</h2>
        <form onSubmit={handleUpload} className="flex flex-col gap-4 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label className="label" htmlFor="import-file">Excel (.xlsx) or CSV file</label>
            <input
              id="import-file"
              type="file"
              accept=".xlsx,.xlsm,.csv"
              className="input"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
            />
          </div>
          <div className="sm:w-64">
            <label className="label" htmlFor="import-station">Station (optional if detected)</label>
            <select id="import-station" className="input" value={stationId}
              onChange={(event) => setStationId(event.target.value)}>
              <option value="">Auto-detect from metadata</option>
              {(stationsQuery.data?.data || []).map((station) => (
                <option key={station.id} value={station.id}>{station.station_code} — {station.name}</option>
              ))}
            </select>
          </div>
          <button type="submit" className="btn-primary" disabled={!file || uploadMutation.isPending}>
            {uploadMutation.isPending ? 'Inspecting…' : 'Upload & inspect'}
          </button>
        </form>
        {uploadMutation.isError && (
          <p className="mt-3 text-sm text-red-600">{extractError(uploadMutation.error)}</p>
        )}
      </div>

      <div className="card overflow-hidden">
        <div className="border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-900">Import history</h2>
        </div>
        {importsQuery.isLoading ? <LoadingSpinner /> : importsQuery.isError ? (
          <ErrorState message={extractError(importsQuery.error)} onRetry={importsQuery.refetch} />
        ) : (
          <>
            <DataTable rows={importsQuery.data?.data || []} columns={historyColumns} emptyMessage="No imports yet." />
            <Pagination meta={importsQuery.data?.meta} onPageChange={setPage} />
          </>
        )}
      </div>

      {selectedBatch && (
        <Modal
          title={`Import preview — ${selectedBatch.original_filename}`}
          description="Review the detected mapping. Correct it if needed, then confirm the import."
          wide
          onClose={() => setSelectedBatch(null)}
          footer={
            <>
              <button type="button" className="btn-secondary" onClick={() => setSelectedBatch(null)}>Cancel</button>
              <button type="button" className="btn-secondary" disabled={!draftMapping || mappingMutation.isPending}
                onClick={() => mappingMutation.mutate({ id: selectedBatch.id, payload: mapping })}>
                Save mapping
              </button>
              <button type="button" className="btn-primary" disabled={selectedBatch.status === 'COMPLETED' || saveAndProcessBusy()}
                onClick={saveAndProcess}>
                {processMutation.isPending ? 'Processing…' : 'Save & process'}
              </button>
            </>
          }
        >
          {previewQuery.isLoading ? <LoadingSpinner /> : previewQuery.isError ? (
            <ErrorState message={extractError(previewQuery.error)} onRetry={previewQuery.refetch} />
          ) : (
            <div className="space-y-5">
              {activeBatchId && <ImportProgressBar progress={progressQuery.data} />}
              {preview?.mapping ? (
                <div className="grid gap-3 rounded-md bg-slate-50 p-3 sm:grid-cols-2">
                  <div>
                    <label className="label">Worksheet</label>
                    <select className="input" value={mapping.sheet_name || ''}
                      onChange={(e) => setDraftMapping({ ...mapping, sheet_name: e.target.value })}>
                      {(selectedBatch.sheet_names || [mapping.sheet_name].filter(Boolean)).map((name) => (
                        <option key={name} value={name}>{name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="label">Station</label>
                    <select className="input" value={mapping.station_id || ''}
                      onChange={(event) => updateMappingField('station_id', event.target.value ? Number(event.target.value) : null)}>
                      <option value="">Not selected</option>
                      {(stationsQuery.data?.data || []).map((station) => (
                        <option key={station.id} value={station.id}>{station.station_code} — {station.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="label">Timestamp column</label>
                    <select className="input" value={mapping.timestamp_column || ''}
                      onChange={(event) => updateMappingField('timestamp_column', event.target.value)}>
                      <option value="">Select…</option>
                      {headers.map((header) => <option key={header}>{header}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="label">Port / channel column</label>
                    <select className="input" value={mapping.port_column || ''}
                      onChange={(event) => updateMappingField('port_column', event.target.value)}>
                      <option value="">None</option>
                      {headers.map((header) => <option key={header}>{header}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="label">Timezone</label>
                    <input className="input" value={mapping.timezone || ''}
                      onChange={(event) => updateMappingField('timezone', event.target.value)}
                      placeholder="Asia/Manila or UTC+08:00" />
                  </div>
                </div>
              ) : null}

              {mapping.metadata?.station && (
                <div className="rounded-md bg-slate-50 p-3">
                  <h3 className="mb-2 text-sm font-semibold text-slate-800">Detected metadata (from the Metadata sheet)</h3>
                  <div className="grid gap-2 text-xs text-slate-600 sm:grid-cols-3">
                    <span><strong>Station:</strong> {mapping.metadata.station.code} — {mapping.metadata.station.name}</span>
                    <span><strong>Site:</strong> {mapping.metadata.station.site || '—'}</span>
                    <span><strong>Device serial:</strong> {mapping.metadata.station.device_serial || '—'}</span>
                    <span><strong>Interval:</strong> {mapping.metadata.station.interval_seconds ?? '—'} s</span>
                    <span><strong>Timezone:</strong> {mapping.metadata.station.timezone || '—'}</span>
                    <span><strong>Logger time:</strong> {mapping.metadata.station.logger_time || '—'}</span>
                  </div>
                  {mapping.metadata.sensors?.length > 0 && (
                    <p className="mt-2 text-xs text-slate-600">
                      <strong>Sensors in metadata:</strong>{' '}
                      {mapping.metadata.sensors.map((sensor) => `Port ${sensor.port}: ${sensor.Name || 'unknown'}`).join(' · ')}
                    </p>
                  )}
                </div>
              )}

              <div>
                <h3 className="mb-2 text-sm font-semibold text-slate-800">Measurement columns</h3>
                <div className="space-y-1">
                  {Object.entries(mapping.measurement_columns || {}).map(([header, code]) => (
                    <div key={header} className="flex items-center gap-2 text-sm">
                      <input type="checkbox" checked
                        onChange={(event) => {
                          const next = { ...mapping.measurement_columns }
                          if (event.target.checked) next[header] = code
                          else delete next[header]
                          updateMappingField('measurement_columns', next)
                        }} />
                      <span className="w-56 truncate text-slate-700">
                        {header}
                        {mapping.measurement_ports?.[header] && (
                          <span className="ml-1 text-[10px] text-slate-400">
                            (port {mapping.measurement_ports[header]})
                          </span>
                        )}
                      </span>
                      <select className="input py-1 text-xs"
                        value={code}
                        onChange={(event) => updateMappingField('measurement_columns', {
                          ...mapping.measurement_columns, [header]: event.target.value,
                        })}>
                        {(typesQuery.data || []).map((type) => (
                          <option key={type.id} value={type.code}>{type.name} ({type.unit})</option>
                        ))}
                      </select>
                    </div>
                  ))}
                </div>
              </div>

              {portValues.length > 0 && (
                <div>
                  <h3 className="mb-2 text-sm font-semibold text-slate-800">Port → sensor mapping</h3>
                  <p className="mb-2 text-xs text-slate-500">Ports are not mapped automatically, so no equipment is invented.</p>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {portValues.map((port) => (
                      <div key={String(port)} className="flex items-center gap-2 text-sm">
                        <span className="w-16 font-medium">Port {String(port)}</span>
                        <select className="input py-1 text-xs"
                          value={(mapping.sensor_mapping || {})[String(port)] || ''}
                          onChange={(event) => updateMappingField('sensor_mapping', {
                            ...(mapping.sensor_mapping || {}),
                            [String(port)]: event.target.value,
                          })}>
                          <option value="">Unassigned</option>
                          {(sensorsQuery.data?.data || []).map((sensor) => (
                            <option key={sensor.id} value={sensor.id}>{sensor.name} ({sensor.model || '—'})</option>
                          ))}
                        </select>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <h3 className="mb-2 text-sm font-semibold text-slate-800">
                  Validation preview ({preview?.row_count || 0} of {preview?.total_rows || 0} rows)
                </h3>
                <div className="max-h-72 overflow-auto rounded border border-slate-200">
                  <table className="min-w-full divide-y divide-slate-200 text-xs">
                    <thead className="bg-slate-50 text-left text-slate-500">
                      <tr>
                        <th className="px-3 py-2">Row</th>
                        <th className="px-3 py-2">Observed at</th>
                        <th className="px-3 py-2">Values</th>
                        <th className="px-3 py-2">Notes</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {(preview?.rows || []).map((row) => (
                        <tr key={row.raw_record_id}>
                          <td className="px-3 py-2">{row.row_number}</td>
                          <td className="px-3 py-2">{row.observation_time ? new Date(row.observation_time).toLocaleString() : '—'}</td>
                          <td className="px-3 py-2">
                            {row.values.map((value) => (
                              <div key={value.header}>
                                <StatusBadge status={value.quality_status} /> {value.code}: {value.normalized_value ?? '—'} {value.is_duplicate && '(duplicate)'}
                              </div>
                            ))}
                          </td>
                          <td className="px-3 py-2 text-slate-600">{row.messages.join('; ') || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {(mappingMutation.isError || processMutation.isError) && (
                <p className="text-sm text-red-600">
                  {extractError(mappingMutation.error || processMutation.error)}
                </p>
              )}
            </div>
          )}
        </Modal>
      )}
    </div>
  )

  function saveAndProcessBusy() {
    return mappingMutation.isPending || processMutation.isPending
  }
}
