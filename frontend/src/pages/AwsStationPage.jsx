import { useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle } from 'lucide-react'
import TrendChart from '../components/charts/TrendChart'
import StationForm from '../components/forms/StationForm'
import DataTable from '../components/ui/DataTable'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import Modal from '../components/ui/Modal'
import PageHeader from '../components/ui/PageHeader'
import SearchableSelect from '../components/ui/SearchableSelect'
import StatusBadge from '../components/ui/StatusBadge'
import SummaryCard from '../components/ui/SummaryCard'
import { useStationImports } from '../hooks/useImports'
import {
  useDataGaps,
  useLatestMeasurements,
  useObservationRange,
  useStatistics,
  useTrends,
} from '../hooks/useMeasurements'
import { useMeasurementTypes } from '../hooks/useSensors'
import { useStation } from '../hooks/useStations'
import { extractError } from '../services/api'
import importService from '../services/importService'
import measurementService from '../services/measurementService'
import stationService from '../services/stationService'
import { stationTypeLabel } from '../utils/stations'

function dateInputToIso(value, endOfDay = false) {
  if (!value) return undefined
  const date = new Date(
    endOfDay ? `${value}T23:59:59Z` : `${value}T00:00:00Z`,
  )
  return Number.isNaN(date.getTime()) ? undefined : date.toISOString()
}

const CATEGORIES = [
  'ATMOSPHERIC', 'WIND', 'PRECIPITATION', 'SOLAR', 'SOIL',
  'HYDROLOGY', 'WATER', 'EQUIPMENT',
]

/**
 * Analytics view for one station. Used by AWS (station from the route) and by
 * AWLS, which fixes the station to NAMNAMA and limits sensors to water-level
 * equipment.
 */
export default function AwsStationPage({
  fixedStationId,
  allowedTypeCodes,
  brand = 'AWS',
  description = 'Analytics: statistics, trends and the latest readings for this site.',
}) {
  const { stationId: routeStationId } = useParams()
  const stationId = fixedStationId || routeStationId
  const stationQuery = useStation(stationId)
  const typesQuery = useMeasurementTypes()
  const [typeId, setTypeId] = useState('')
  const [days, setDays] = useState(3650)
  const [interval, setInterval] = useState(60)
  const [yMin, setYMin] = useState(0) // suggested starting point for AWS charts
  const [yMax, setYMax] = useState('') // blank = let the chart choose
  const [yStep, setYStep] = useState(5) // tick interval; editable by the user
  const [fillNotice, setFillNotice] = useState('')
  const [exportNotice, setExportNotice] = useState('')
  const [exporting, setExporting] = useState(false)
  const [clearOpen, setClearOpen] = useState(false)
  const [clearPassword, setClearPassword] = useState('')
  const [clearNotice, setClearNotice] = useState('')
  const [editOpen, setEditOpen] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploadFile, setUploadFile] = useState(null)
  const [uploadNotice, setUploadNotice] = useState('')
  const [customFrom, setCustomFrom] = useState('')
  const [customTo, setCustomTo] = useState('')
  const queryClient = useQueryClient()

  const fillMutation = useMutation({
    mutationFn: () => measurementService.fillGaps(stationId, effectiveTypeId),
    onSuccess: (result) => {
      setFillNotice(
        `Filled ${result.created_rows} missing timestamp${result.created_rows === 1 ? '' : 's'} with empty values.`,
      )
      queryClient.invalidateQueries({ queryKey: ['measurements'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['data-quality'] })
    },
  })

  const clearDataMutation = useMutation({
    mutationFn: (password) => stationService.clearData(stationId, password),
    onSuccess: (result) => {
      setClearOpen(false)
      setClearPassword('')
      queryClient.invalidateQueries({ queryKey: ['measurements'] })
      queryClient.invalidateQueries({ queryKey: ['imports'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['data-quality'] })
      setClearNotice(
        `Cleared ${result?.measurements_deleted?.toLocaleString() ?? 0} readings ` +
        `and ${result?.import_batches_deleted ?? 0} import(s). Re-upload the correct file.`,
      )
    },
  })

  const editMutation = useMutation({
    mutationFn: (payload) => stationService.update(stationId, payload),
    onSuccess: (updated) => {
      setEditOpen(false)
      queryClient.invalidateQueries({ queryKey: ['stations', stationId] })
      queryClient.invalidateQueries({ queryKey: ['stations'] })
      setClearNotice(`Station saved as ${updated.name} (${updated.station_code}).`)
    },
  })

  const uploadMutation = useMutation({
    mutationFn: async (file) => {
      const formData = new FormData()
      formData.append('file', file)
      // Lock this import to the station shown on this page.
      formData.append('station_id', stationId)
      const batch = await importService.upload(formData)
      const result = await importService.process(batch.id)
      return { batch, result }
    },
    onSuccess: ({ result }) => {
      setUploadOpen(false)
      setUploadFile(null)
      queryClient.invalidateQueries({ queryKey: ['measurements'] })
      queryClient.invalidateQueries({ queryKey: ['imports'] })
      queryClient.invalidateQueries({ queryKey: ['stations', stationId] })
      const summary = result?.summary || {}
      setUploadNotice(
        `Import complete: ${summary.imported_rows ?? 0} new readings, ` +
        `${summary.duplicate_rows ?? 0} duplicates skipped.`,
      )
    },
  })

  const types = (typesQuery.data || []).filter(
    (type) => !allowedTypeCodes || allowedTypeCodes.includes(type.code),
  )
  // When a station has a fixed sensor set, prefer the first code in that list
  // (e.g. water_level for AWLS) rather than whatever order the API returned.
  const effectiveTypeId =
    typeId ||
    (allowedTypeCodes
      ? allowedTypeCodes
          .map((code) => types.find((type) => type.code === code)?.id)
          .find(Boolean)
      : types[0]?.id)

  const presetFrom = useMemo(
    () => new Date(Date.now() - days * 86400000).toISOString(),
    [days],
  )
  // Explicit From/To inputs override the preset dropdown for the whole view.
  const dateFrom = dateInputToIso(customFrom) ?? presetFrom
  const dateTo = dateInputToIso(customTo, true)
  const rangeInvalid = Boolean(
    customFrom && customTo && customFrom > customTo,
  )
  const dateFilters = { date_from: dateFrom, ...(dateTo ? { date_to: dateTo } : {}) }

  const statsQuery = useStatistics({
    station_id: stationId,
    measurement_type_id: effectiveTypeId,
    ...dateFilters,
  })
  const trendsQuery = useTrends({
    station_id: stationId,
    measurement_type_ids: effectiveTypeId ? [Number(effectiveTypeId)] : [],
    interval_minutes: interval,
    ...dateFilters,
  })
  const latestQuery = useLatestMeasurements({ station_id: stationId, ...dateFilters })
  const rangeQuery = useObservationRange({ station_id: stationId, ...dateFilters })
  const gapsQuery = useDataGaps({
    station_id: stationId,
    measurement_type_id: effectiveTypeId,
    ...dateFilters,
  })
  const importsQuery = useStationImports(stationId)

  const sourceColumns = [
    {
      key: 'file',
      label: 'Source file',
      render: (row) => (
        <>
          <span className="font-medium">{row.original_filename}</span>
          <span className="block text-xs text-slate-500">{row.batch_number}</span>
        </>
      ),
    },
    {
      key: 'size',
      label: 'Size',
      render: (row) =>
        row.file_size_bytes ? `${(row.file_size_bytes / 1024 / 1024).toFixed(2)} MB` : '—',
    },
    { key: 'rows', label: 'Rows imported', render: (row) => row.imported_rows ?? 0 },
    {
      key: 'status',
      label: 'Status',
      render: (row) => (
        <StatusBadge
          status={
            row.status === 'COMPLETED'
              ? 'VALID'
              : row.status === 'FAILED'
                ? 'INVALID'
                : 'UNVERIFIED'
          }
        />
      ),
    },
    {
      key: 'uploaded',
      label: 'Uploaded (UTC)',
      render: (row) =>
        row.file_imported_at ? new Date(row.file_imported_at).toLocaleString() : '—',
    },
    {
      key: 'download',
      label: '',
      render: (row) => (
        <button
          type="button"
          className="btn-secondary px-2 py-1 text-xs"
          onClick={() => importService.downloadSource(row.id, row.original_filename)}
        >
          Download
        </button>
      ),
    },
  ]

  const columns = [
    {
      key: 'type',
      label: 'Parameter',
      render: (row) =>
        types.find((type) => type.id === row.measurement_type_id)?.name ||
        `#${row.measurement_type_id}`,
    },
    {
      key: 'value',
      label: 'Value',
      render: (row) =>
        `${row.normalized_value ?? row.original_value ?? '—'} ${row.unit || ''}`,
    },
    { key: 'sensor', label: 'Sensor', render: (row) => row.sensor_id ?? '—' },
    {
      key: 'observed',
      label: 'Observed at (UTC)',
      render: (row) => new Date(row.observation_time).toLocaleString(),
    },
    { key: 'quality', label: 'Quality', render: (row) => <StatusBadge status={row.quality_status} /> },
  ]

  if (stationQuery.isLoading || typesQuery.isLoading) {
    return <LoadingSpinner label="Loading AWS station…" />
  }
  if (stationQuery.isError || !stationQuery.data) {
    return (
      <ErrorState
        message={stationQuery.isError ? extractError(stationQuery.error) : 'Station not found.'}
        onRetry={stationQuery.refetch}
      />
    )
  }
  if (typesQuery.isError) {
    return <ErrorState message="Could not load measurement types." onRetry={typesQuery.refetch} />
  }

  const station = stationQuery.data
  const stats = statsQuery.data
  const readings = latestQuery.data || []
  const coverage = rangeQuery.data
  const sourceFiles = importsQuery.data?.data || []

  const handleExport = async () => {
    setExporting(true)
    setExportNotice('')
    try {
      await measurementService.exportSource(
        { station_id: stationId, ...dateFilters },
        `${brand}_${station.name}_source.xlsx`,
      )
    } catch (err) {
      setExportNotice(`Export failed: ${extractError(err)}`)
    } finally {
      setExporting(false)
    }
  }
  const yMinValue = yMin === '' || Number.isNaN(Number(yMin)) ? undefined : Number(yMin)
  const yMaxValue = yMax === '' || Number.isNaN(Number(yMax)) ? undefined : Number(yMax)
  const yStepValue =
    yStep === '' || Number.isNaN(Number(yStep)) || Number(yStep) <= 0
      ? undefined
      : Number(yStep)

  return (
    <div>
      <PageHeader
        title={`${brand} — ${station.name}`}
        description={`${stationTypeLabel(station.station_type)} · ${description}`}
        actions={
          <>
            <button type="button" className="btn-secondary" onClick={() => setEditOpen(true)}>
              Edit station
            </button>
            <button type="button" className="btn-secondary" onClick={() => { setUploadNotice(''); setUploadOpen(true) }}>
              Upload data
            </button>
            <button
              type="button"
              className="btn-secondary border-red-300 text-red-700 hover:bg-red-50"
              onClick={() => { setClearPassword(''); setClearNotice(''); setClearOpen(true) }}
            >
              Clear data
            </button>
            <button
              type="button"
              className="btn-secondary"
              disabled={exporting}
              onClick={handleExport}
            >
              {exporting ? 'Preparing Excel…' : 'Export Excel (source format)'}
            </button>
          </>
        }
      />

      {exportNotice && (
        <p className="mb-4 text-sm text-red-700">{exportNotice}</p>
      )}
      {clearNotice && (
        <p className="mb-4 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">
          {clearNotice}
        </p>
      )}
      {uploadNotice && (
        <p className="mb-4 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">
          {uploadNotice}
        </p>
      )}

      <section className="card mb-4 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">{station.name}</h2>
            <p className="text-xs text-slate-500">
              {station.site_name || 'No site name'} · {station.station_code}
            </p>
          </div>
          <StatusBadge status={station.operational_status} />
        </div>
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-xs sm:grid-cols-4">
          <div>
            <dt className="text-slate-500">Coordinates</dt>
            <dd className="font-medium text-slate-800">
              {station.latitude != null && station.longitude != null
                ? `${station.latitude}, ${station.longitude}`
                : 'Not surveyed'}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Timezone</dt>
            <dd className="font-medium text-slate-800">{station.timezone}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Interval</dt>
            <dd className="font-medium text-slate-800">
              {station.measurement_interval_seconds ?? 900} s
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Device serial</dt>
            <dd className="font-medium text-slate-800">{station.device_serial_number || '—'}</dd>
          </div>
        </dl>
      </section>

      <section className="card mb-4 p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">Data coverage</h2>
        {rangeQuery.isLoading ? (
          <LoadingSpinner />
        ) : rangeQuery.isError ? (
          <ErrorState message="Could not load data coverage." onRetry={rangeQuery.refetch} />
        ) : (
          <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-xs text-slate-500">First observation (UTC)</dt>
              <dd className="font-medium text-slate-800">
                {coverage?.first_observation
                  ? new Date(coverage.first_observation).toLocaleString()
                  : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Last observation (UTC)</dt>
              <dd className="font-medium text-slate-800">
                {coverage?.last_observation
                  ? new Date(coverage.last_observation).toLocaleString()
                  : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Stored measurements</dt>
              <dd className="font-medium text-slate-800">
                {coverage?.total_measurements?.toLocaleString() ?? 0}
              </dd>
            </div>
          </dl>
        )}
      </section>

      {gapsQuery.data?.total_gaps > 0 && (
        <section className="card mb-4 border-amber-300 bg-amber-50 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-600" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-amber-900">
                {gapsQuery.data.total_gaps} data gap
                {gapsQuery.data.total_gaps === 1 ? '' : 's'} detected —{' '}
                {gapsQuery.data.total_missing_readings.toLocaleString()} missing
                reading
                {gapsQuery.data.total_missing_readings === 1 ? '' : 's'}
              </p>
              <p className="mt-1 text-xs text-amber-800">
                Expected interval: {gapsQuery.data.interval_seconds}s. Timestamps
                jump without any stored reading; source data is never filled in
                or invented.
              </p>
              <details className="mt-2 text-xs text-amber-900">
                <summary className="cursor-pointer font-medium">Show gaps</summary>
                <ul className="mt-2 max-h-40 space-y-1 overflow-y-auto">
                  {gapsQuery.data.gaps.slice(0, 20).map((gap, index) => (
                    <li key={`${gap.start}-${index}`}>
                      {new Date(gap.start).toLocaleString()} →{' '}
                      {new Date(gap.end).toLocaleString()} —{' '}
                      {gap.missing_readings} missing ({gap.gap_minutes} min jump)
                    </li>
                  ))}
                </ul>
              </details>
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  className="btn-secondary px-3 py-1.5 text-xs"
                  disabled={!effectiveTypeId || fillMutation.isPending}
                  onClick={() => {
                    setFillNotice('')
                    fillMutation.mutate()
                  }}
                >
                  {fillMutation.isPending
                    ? 'Filling…'
                    : `Fill ${gapsQuery.data.total_missing_readings} missing timestamp${gapsQuery.data.total_missing_readings === 1 ? '' : 's'}`}
                </button>
                <span className="text-xs text-amber-900">
                  Adds timestamp-only rows with empty values (status MISSING).
                </span>
              </div>
              {fillNotice && (
                <p className="mt-2 text-xs font-medium text-green-800">{fillNotice}</p>
              )}
              {fillMutation.isError && (
                <p className="mt-2 text-xs text-red-700">
                  {extractError(fillMutation.error)}
                </p>
              )}
            </div>
          </div>
        </section>
      )}

      <div className="card mb-4 p-4">
        <div className="flex flex-wrap items-end gap-x-4 gap-y-3">
          <div className="w-full sm:w-52">
            <label className="label">Parameter</label>
            <SearchableSelect
              className="w-full"
              value={effectiveTypeId || ''}
              onChange={(value) => setTypeId(Number(value))}
              placeholder="Choose a measurement type…"
              groups={CATEGORIES.map((category) => ({
                label: category,
                options: types
                  .filter((type) => type.category === category)
                  .map((type) => ({ value: type.id, label: type.name, description: type.unit })),
              })).filter((group) => group.options.length > 0)}
            />
          </div>
          <div className="w-full sm:w-36">
            <label className="label" htmlFor="aws-days">Date range</label>
            <select
              id="aws-days"
              className="input"
              value={days}
              onChange={(event) => setDays(Number(event.target.value))}
            >
              <option value={1}>Last 24 hours</option>
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
              <option value={365}>Last year</option>
              <option value={3650}>All dates</option>
            </select>
          </div>
          <div className="w-full sm:w-36">
            <label className="label" htmlFor="aws-date-from">From</label>
            <input
              id="aws-date-from"
              type="date"
              className="input"
              value={customFrom}
              onChange={(event) => setCustomFrom(event.target.value)}
            />
          </div>
          <div className="w-full sm:w-36">
            <label className="label" htmlFor="aws-date-to">To</label>
            <input
              id="aws-date-to"
              type="date"
              className="input"
              value={customTo}
              onChange={(event) => setCustomTo(event.target.value)}
            />
          </div>
          {(customFrom || customTo) && (
            <button
              type="button"
              className="btn-secondary px-3"
              onClick={() => { setCustomFrom(''); setCustomTo('') }}
            >
              Clear dates
            </button>
          )}
          <div className="w-full sm:w-36">
            <label className="label">Interval</label>
            <SearchableSelect
              className="w-full"
              value={interval}
              onChange={(value) => setInterval(Number(value))}
              placeholder="Aggregation interval"
              groups={[{
                label: 'Time interval',
                options: [
                  { value: 15, label: '15 minutes' },
                  { value: 60, label: 'Hourly' },
                  { value: 1440, label: 'Daily' },
                ],
              }]}
            />
          </div>
          <div className="w-20">
            <label className="label" htmlFor="aws-y-min">Y min</label>
            <input
              id="aws-y-min"
              type="number"
              className="input"
              value={yMin}
              onChange={(event) => setYMin(event.target.value)}
              placeholder="0"
              title="Suggested: 0"
            />
          </div>
          <div className="w-20">
            <label className="label" htmlFor="aws-y-max">Y max</label>
            <input
              id="aws-y-max"
              type="number"
              className="input"
              value={yMax}
              onChange={(event) => setYMax(event.target.value)}
              placeholder="Auto"
              title="Leave blank to let the chart choose the maximum"
            />
          </div>
          <div className="w-16">
            <label className="label" htmlFor="aws-y-step">Step</label>
            <input
              id="aws-y-step"
              type="number"
              min="1"
              className="input"
              value={yStep}
              onChange={(event) => setYStep(event.target.value)}
              placeholder="5"
              title="Tick interval, e.g. 3, 5 or 10"
            />
          </div>
          <button
            type="button"
            className="btn-secondary px-3"
            onClick={() => { setYMin(0); setYMax(''); setYStep(5) }}
            title="Suggested: min 0, max Auto, step 5"
          >
            Reset
          </button>
        </div>
        {(customFrom || customTo) && (
          <p className="mt-3 text-xs font-medium text-brand-700">
            Custom From/To dates are active and override the Date range dropdown.
            {rangeInvalid ? ' From must be on or before To.' : ''}
          </p>
        )}
        <p className="mt-3 text-xs text-slate-500">
          Suggested: min 0, max Auto, step 5. Type your own numbers to override.
        </p>
      </div>

      {statsQuery.isLoading ? (
        <LoadingSpinner />
      ) : statsQuery.isError ? (
        <ErrorState message={extractError(statsQuery.error)} onRetry={statsQuery.refetch} />
      ) : (
        <section className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-8">
          <SummaryCard label="Observations" value={stats?.observations ?? 0} />
          <SummaryCard label="Minimum" value={stats?.min ?? '—'} hint={stats?.unit} />
          <SummaryCard label="Maximum" value={stats?.max ?? '—'} hint={stats?.unit} />
          <SummaryCard label="Average" value={stats?.average ?? '—'} hint={stats?.unit} />
          <SummaryCard label="Median" value={stats?.median ?? '—'} hint={stats?.unit} />
          <SummaryCard label="Std deviation" value={stats?.std_dev ?? '—'} />
          <SummaryCard label="Total" value={stats?.total ?? '—'} hint={stats?.unit} />
          <SummaryCard
            label="Completeness"
            value={stats?.completeness_percent != null ? `${stats.completeness_percent}%` : '—'}
            hint={`${stats?.missing_records ?? 0} missing`}
          />
        </section>
      )}

      <section className="card mt-6 p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">
          Trend — {stats?.name || 'Select a measurement type'}
        </h2>
        {trendsQuery.isLoading ? (
          <LoadingSpinner />
        ) : trendsQuery.isError ? (
          <ErrorState message="Could not load trend." onRetry={trendsQuery.refetch} />
        ) : (
          <TrendChart
            series={trendsQuery.data || []}
            unit={stats?.unit}
            height={360}
            yMin={yMinValue}
            yMax={yMaxValue}
            yStep={yStepValue}
          />
        )}
      </section>

      <section className="card mt-6 p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">Latest readings</h2>
        {latestQuery.isLoading ? (
          <LoadingSpinner />
        ) : latestQuery.isError ? (
          <ErrorState message="Could not load latest readings." onRetry={latestQuery.refetch} />
        ) : readings.length === 0 ? (
          <EmptyState
            title="No readings for this station yet"
            description="Import an Excel or CSV file for this station; readings will appear here automatically."
          />
        ) : (
          <DataTable columns={columns} rows={readings} keyField="id" />
        )}
      </section>

      <section className="card mt-6 p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">
          Source workbooks (preserved uploads)
        </h2>
        {importsQuery.isLoading ? (
          <LoadingSpinner />
        ) : importsQuery.isError ? (
          <ErrorState message="Could not load upload history." onRetry={importsQuery.refetch} />
        ) : sourceFiles.length === 0 ? (
          <EmptyState
            title="No workbooks uploaded for this station"
            description="The original Excel/CSV files and their raw rows are kept after every import."
          />
        ) : (
          <DataTable columns={sourceColumns} rows={sourceFiles} keyField="id" />
        )}
      </section>

      {clearOpen && (
        <Modal
          title={`Clear data for ${station.name}`}
          description="This cannot be undone."
          onClose={() => setClearOpen(false)}
          footer={<>
            <button type="button" className="btn-secondary" onClick={() => setClearOpen(false)}
              disabled={clearDataMutation.isPending}>Cancel</button>
            <button type="button" className="btn-primary bg-red-600 hover:bg-red-700"
              disabled={!clearPassword || clearDataMutation.isPending}
              onClick={() => clearDataMutation.mutate(clearPassword)}>
              {clearDataMutation.isPending ? 'Clearing…' : 'Clear all data'}
            </button>
          </>}
        >
          <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            This permanently deletes all readings, quality flags, alerts and import
            batches for <strong>{station.name}</strong>. The station, its sensors and
            configuration are kept. Re-upload the correct file afterwards.
          </div>
          <label className="label mt-4" htmlFor="aws-clear-password">
            Confirm with your admin password
          </label>
          <input
            id="aws-clear-password"
            type="password"
            className="input"
            autoComplete="current-password"
            value={clearPassword}
            onChange={(event) => setClearPassword(event.target.value)}
            placeholder="Enter your password"
          />
          {clearDataMutation.isError && (
            <p className="mt-2 text-sm text-red-600">{extractError(clearDataMutation.error)}</p>
          )}
        </Modal>
      )}

      {editOpen && (
        <Modal
          title="Edit station"
          description="Change the station code, name or settings."
          onClose={() => setEditOpen(false)}
        >
          <StationForm
            station={station}
            isWorking={editMutation.isPending}
            submitLabel="Save station"
            onCancel={() => setEditOpen(false)}
            onSubmit={(payload) => editMutation.mutate(payload)}
          />
          {editMutation.isError && (
            <p className="mt-2 text-sm text-red-600">{extractError(editMutation.error)}</p>
          )}
        </Modal>
      )}

      {uploadOpen && (
        <Modal
          title={`Upload data for ${station.name}`}
          description="The file is locked to this station."
          onClose={() => setUploadOpen(false)}
          footer={<>
            <button type="button" className="btn-secondary" onClick={() => setUploadOpen(false)}
              disabled={uploadMutation.isPending}>Cancel</button>
            <button type="button" className="btn-primary"
              disabled={!uploadFile || uploadMutation.isPending}
              onClick={() => uploadMutation.mutate(uploadFile)}>
              {uploadMutation.isPending ? 'Uploading & importing…' : 'Upload & import'}
            </button>
          </>}
        >
          <label className="label" htmlFor="aws-upload-file">Excel or CSV file</label>
          <input
            id="aws-upload-file"
            type="file"
            accept=".xlsx,.xlsm,.csv"
            className="input"
            onChange={(event) => setUploadFile(event.target.files?.[0] || null)}
          />
          <p className="mt-2 text-xs text-slate-500">
            Station: <strong>{station.name}</strong> ({station.station_code}).
            Existing readings are never overwritten; duplicates are skipped.
          </p>
          {uploadMutation.isError && (
            <p className="mt-2 text-sm text-red-600">{extractError(uploadMutation.error)}</p>
          )}
        </Modal>
      )}
    </div>
  )
}
