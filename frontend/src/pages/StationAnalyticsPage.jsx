import { useMemo, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import TrendChart from '../components/charts/TrendChart'
import DataTable from '../components/ui/DataTable'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import PageHeader from '../components/ui/PageHeader'
import SearchableSelect from '../components/ui/SearchableSelect'
import StatusBadge from '../components/ui/StatusBadge'
import SummaryCard from '../components/ui/SummaryCard'
import {
  useFlexibleComparison,
  useLatestMeasurements,
  useTrends,
} from '../hooks/useMeasurements'
import { useDataCompleteness } from '../hooks/useAccomplishment'
import { useQualityFlags } from '../hooks/useMonitoring'
import { useMeasurementTypes } from '../hooks/useSensors'
import { useStation } from '../hooks/useStations'
import { extractError } from '../services/api'
import measurementService from '../services/measurementService'

const CATEGORIES = [
  'ATMOSPHERIC', 'WIND', 'PRECIPITATION', 'SOLAR', 'SOIL',
  'EQUIPMENT', 'HYDROLOGY', 'WATER',
]

export default function StationAnalyticsPage() {
  const { id } = useParams()
  const stationId = Number(id)
  const stationQuery = useStation(stationId)
  const typesQuery = useMeasurementTypes()
  const [typeId, setTypeId] = useState('')
  const [interval, setInterval] = useState(60)
  const [days, setDays] = useState(3650)
  const [statsRange, setStatsRange] = useState({ from: '', to: '' })
  const [statsCompare, setStatsCompare] = useState({
    from_a: '2025-07-01', to_a: '2025-08-15',
    from_b: '2025-08-16', to_b: '2025-09-30',
  })

  const types = typesQuery.data || []
  const effectiveTypeId = typeId || types[0]?.id
  const dateFrom = useMemo(
    () => new Date(Date.now() - days * 86400000).toISOString(),
    [days],
  )

  // ONE request for every measurement type instead of one per type.
  const statsQuery = useQuery({
    queryKey: ['measurements', 'statistics-bulk', stationId, statsRange.from, statsRange.to],
    queryFn: () => measurementService.statisticsBulk(stationId, statsRange.from, statsRange.to),
    enabled: Boolean(stationId),
    staleTime: 60_000,
  })
  const statsAQuery = useQuery({
    queryKey: ['measurements', 'statistics-bulk', stationId, statsCompare.from_a, statsCompare.to_a],
    queryFn: () => measurementService.statisticsBulk(stationId, statsCompare.from_a, statsCompare.to_a),
    enabled: Boolean(stationId && statsCompare.from_a && statsCompare.to_a),
  })
  const statsBQuery = useQuery({
    queryKey: ['measurements', 'statistics-bulk', stationId, statsCompare.from_b, statsCompare.to_b],
    queryFn: () => measurementService.statisticsBulk(stationId, statsCompare.from_b, statsCompare.to_b),
    enabled: Boolean(stationId && statsCompare.from_b && statsCompare.to_b),
  })
  const trendsQuery = useTrends({
    station_id: stationId,
    measurement_type_ids: effectiveTypeId ? [Number(effectiveTypeId)] : [],
    interval_minutes: interval,
    // Use the same range as the measurement statistics table when one is set.
    date_from: statsRange.from || dateFrom,
    date_to: statsRange.to || undefined,
  })
  const compareQuery = useFlexibleComparison({
    station_id: stationId,
    measurement_type_id: effectiveTypeId,
    date_from_a: statsCompare.from_a,
    date_to_a: statsCompare.to_a,
    date_from_b: statsCompare.from_b,
    date_to_b: statsCompare.to_b,
    interval_minutes: interval,
  })
  const latestQuery = useLatestMeasurements({ station_id: stationId })
  const completenessQuery = useDataCompleteness({ station_id: stationId })
  const flagsQuery = useQualityFlags({
    station_id: stationId, resolution_status: 'OPEN', per_page: 10,
  })

  if (stationQuery.isLoading || typesQuery.isLoading) return <LoadingSpinner />
  if (stationQuery.isError) return <ErrorState message={extractError(stationQuery.error)} />

  const station = stationQuery.data
  const completeness = completenessQuery.data
  const stats = statsQuery.data || {}

  return (
    <div>
      <PageHeader
        title={`${station.name} — Analytics`}
        description={`${station.station_code} · ${station.site_name || 'No site'} · ${station.timezone}`}
        actions={<Link className="btn-secondary" to={`/stations/${station.id}`}>Station details</Link>}
      />

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <SummaryCard label="Registered sensors" value={station.sensor_count ?? '—'} />
        <SummaryCard label="Measurements" value={station.measurement_count ?? '—'} />
        <SummaryCard label="Data completeness" value={completeness?.completeness_percent != null ? `${completeness.completeness_percent}%` : '—'} />
        <SummaryCard label="Open quality flags" value={flagsQuery.data?.meta?.total ?? '—'} tone="amber" />
      </section>

      <section className="card mt-6 p-4">
        <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Measurement statistics</h2>
            <p className="text-xs text-slate-500">All measurement types stored for this station.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <SearchableSelect
              className="w-56"
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
            <input type="date" className="input py-1 text-xs w-36" title="Statistics from"
              value={statsRange.from}
              onChange={(e) => setStatsRange({ ...statsRange, from: e.target.value })} />
            <input type="date" className="input py-1 text-xs w-36" title="Statistics to"
              value={statsRange.to}
              onChange={(e) => setStatsRange({ ...statsRange, to: e.target.value })} />
            <button type="button" className="btn-secondary py-1 text-xs"
              onClick={() => setStatsRange({ from: '', to: '' })}>
              All dates
            </button>
          </div>
        </div>
        {statsQuery.isLoading ? <LoadingSpinner /> : statsQuery.isError ? (
          <ErrorState message={extractError(statsQuery.error)} onRetry={statsQuery.refetch} />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">Parameter</th><th className="px-3 py-2">Unit</th>
                  <th className="px-3 py-2">N</th><th className="px-3 py-2">Min</th>
                  <th className="px-3 py-2">Max</th><th className="px-3 py-2">Avg</th>
                  <th className="px-3 py-2">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {types.map((type) => {
                  const row = stats[String(type.id)] || {}
                  return (
                    <tr key={type.id} className={type.id === effectiveTypeId ? 'bg-brand-50' : 'hover:bg-slate-50'}>
                      <td className="px-3 py-2">
                        <button className="text-left text-xs font-medium text-brand-700 hover:underline"
                          onClick={() => setTypeId(type.id)}>{type.name}</button>
                      </td>
                      <td className="px-3 py-2 text-xs">{type.unit}</td>
                      <td className="px-3 py-2 text-xs">{row.observations ?? '—'}</td>
                      <td className="px-3 py-2 text-xs">{row.min ?? '—'}</td>
                      <td className="px-3 py-2 text-xs">{row.max ?? '—'}</td>
                      <td className="px-3 py-2 text-xs">{row.average ?? '—'}</td>
                      <td className="px-3 py-2 text-xs">{row.total ?? '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card mt-6 p-4">
        <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-sm font-semibold text-slate-900">Trend</h2>
          <div className="w-40">
            <SearchableSelect
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
        </div>
        {trendsQuery.isLoading ? <LoadingSpinner /> : trendsQuery.isError ? (
          <ErrorState message={extractError(trendsQuery.error)} onRetry={trendsQuery.refetch} />
        ) : (
          <TrendChart series={trendsQuery.data || []} height={320} />
        )}
      </section>

      {/* Compare statistics for two date ranges, for every measurement type */}
      <section className="card mt-6 p-4">
        <div className="mb-4">
          <h2 className="text-sm font-semibold text-slate-900">Statistics comparison</h2>
          <p className="text-xs text-slate-500">
            Compare all parameters between two date ranges. Changes are calculated from each range's average.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded border border-blue-200 bg-blue-50/40 p-3">
            <p className="mb-2 text-xs font-semibold text-blue-800">Range A</p>
            <div className="grid grid-cols-2 gap-2">
              <input type="date" className="input text-xs" value={statsCompare.from_a}
                onChange={(e) => setStatsCompare({ ...statsCompare, from_a: e.target.value })} />
              <input type="date" className="input text-xs" value={statsCompare.to_a}
                onChange={(e) => setStatsCompare({ ...statsCompare, to_a: e.target.value })} />
            </div>
          </div>
          <div className="rounded border border-orange-200 bg-orange-50/40 p-3">
            <p className="mb-2 text-xs font-semibold text-orange-800">Range B</p>
            <div className="grid grid-cols-2 gap-2">
              <input type="date" className="input text-xs" value={statsCompare.from_b}
                onChange={(e) => setStatsCompare({ ...statsCompare, from_b: e.target.value })} />
              <input type="date" className="input text-xs" value={statsCompare.to_b}
                onChange={(e) => setStatsCompare({ ...statsCompare, to_b: e.target.value })} />
            </div>
          </div>
        </div>

        <div className="mt-4">
          {statsAQuery.isLoading || statsBQuery.isLoading ? (
            <LoadingSpinner label="Comparing statistics…" />
          ) : statsAQuery.isError || statsBQuery.isError ? (
            <ErrorState message="Could not load comparison statistics." />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Parameter</th>
                    <th className="px-3 py-2">Avg A</th>
                    <th className="px-3 py-2">Avg B</th>
                    <th className="px-3 py-2">Change</th>
                    <th className="px-3 py-2">% change</th>
                    <th className="px-3 py-2">N (A / B)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {types.map((type) => {
                    const a = statsAQuery.data?.[String(type.id)] || {}
                    const b = statsBQuery.data?.[String(type.id)] || {}
                    const hasBoth = a.average !== null && a.average !== undefined &&
                      b.average !== null && b.average !== undefined
                    const absolute = hasBoth ? b.average - a.average : null
                    const percent = hasBoth && a.average !== 0 ? (absolute / a.average) * 100 : null
                    return (
                      <tr key={type.id} className="hover:bg-slate-50">
                        <td className="px-3 py-2 font-medium">
                          {type.name} <span className="text-xs text-slate-400">({type.unit})</span>
                        </td>
                        <td className="px-3 py-2 tabular-nums">{a.average ?? '—'}</td>
                        <td className="px-3 py-2 tabular-nums">{b.average ?? '—'}</td>
                        <td className={`px-3 py-2 tabular-nums ${absolute > 0 ? 'text-green-700' : absolute < 0 ? 'text-red-700' : ''}`}>
                          {absolute !== null ? `${absolute > 0 ? '+' : ''}${absolute.toFixed(2)}` : '—'}
                        </td>
                        <td className={`px-3 py-2 tabular-nums ${percent > 0 ? 'text-green-700' : percent < 0 ? 'text-red-700' : ''}`}>
                          {percent !== null ? `${percent > 0 ? '+' : ''}${percent.toFixed(1)}%` : '—'}
                        </td>
                        <td className="px-3 py-2 tabular-nums">
                          {a.observations ?? 0} / {b.observations ?? 0}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      {/* Compare two date ranges for this station */}
      <section className="card mt-6 p-4">
        <div className="mb-4">
          <h2 className="text-sm font-semibold text-slate-900">Trend comparison</h2>
          <p className="text-xs text-slate-500">
            Compare two date ranges. Both lines are aligned by elapsed time from the start of each period.
          </p>
        </div>

        {/* Ranges come from the Statistics comparison pickers above. */}
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded border border-blue-200 bg-blue-50/40 p-3 text-xs">
            <p className="font-semibold text-blue-800">Period A</p>
            <p className="mt-1 text-slate-600">
              {statsCompare.from_a || '—'} → {statsCompare.to_a || '—'}
            </p>
          </div>
          <div className="rounded border border-orange-200 bg-orange-50/40 p-3 text-xs">
            <p className="font-semibold text-orange-800">Period B</p>
            <p className="mt-1 text-slate-600">
              {statsCompare.from_b || '—'} → {statsCompare.to_b || '—'}
            </p>
          </div>
        </div>

        <div className="mt-4">
          {compareQuery.isLoading ? <LoadingSpinner /> : compareQuery.isError ? (
            <ErrorState message={extractError(compareQuery.error)} onRetry={compareQuery.refetch} />
          ) : compareQuery.data ? (
            <>
              <TrendChart
                axisType="value"
                xField="offset_hours"
                height={320}
                series={[
                  {
                    name: `Period A (${compareQuery.data.period_a.date_from} → ${compareQuery.data.period_a.date_to})`,
                    points: compareQuery.data.period_a.points,
                  },
                  {
                    name: `Period B (${compareQuery.data.period_b.date_from} → ${compareQuery.data.period_b.date_to})`,
                    points: compareQuery.data.period_b.points,
                  },
                ]}
              />
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                {['period_a', 'period_b'].map((key) => (
                  <div key={key} className="rounded bg-slate-50 p-3 text-sm">
                    <p className="font-semibold">{key === 'period_a' ? 'Period A' : 'Period B'}</p>
                    <p>Observations: {compareQuery.data[key].observations}</p>
                    <p>Average: {compareQuery.data[key].statistics.average ?? 'N/A'} {compareQuery.data.measurement_type.unit}</p>
                    <p>Min / Max: {compareQuery.data[key].statistics.min ?? 'N/A'} / {compareQuery.data[key].statistics.max ?? 'N/A'}</p>
                  </div>
                ))}
              </div>

              {(() => {
                const a = compareQuery.data.period_a.statistics
                const b = compareQuery.data.period_b.statistics
                const unit = compareQuery.data.measurement_type.unit
                const hasBoth = a.average !== null && b.average !== null
                const absolute = hasBoth ? b.average - a.average : null
                const percent = hasBoth && a.average !== 0
                  ? (absolute / a.average) * 100
                  : null
                return (
                  <div className="mt-4 overflow-x-auto">
                    <table className="min-w-full divide-y divide-slate-200 text-sm">
                      <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
                        <tr>
                          <th className="px-3 py-2">Parameter</th>
                          <th className="px-3 py-2">Period A avg</th>
                          <th className="px-3 py-2">Period B avg</th>
                          <th className="px-3 py-2">Change</th>
                          <th className="px-3 py-2">% change</th>
                          <th className="px-3 py-2">Observations (A / B)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        <tr>
                          <td className="px-3 py-2 font-medium">
                            {compareQuery.data.measurement_type.name} ({unit})
                          </td>
                          <td className="px-3 py-2 tabular-nums">{a.average ?? '—'}</td>
                          <td className="px-3 py-2 tabular-nums">{b.average ?? '—'}</td>
                          <td className={`px-3 py-2 tabular-nums ${absolute > 0 ? 'text-green-700' : absolute < 0 ? 'text-red-700' : ''}`}>
                            {absolute !== null ? `${absolute > 0 ? '+' : ''}${absolute.toFixed(2)} ${unit}` : '—'}
                          </td>
                          <td className={`px-3 py-2 tabular-nums ${percent > 0 ? 'text-green-700' : percent < 0 ? 'text-red-700' : ''}`}>
                            {percent !== null ? `${percent > 0 ? '+' : ''}${percent.toFixed(1)}%` : '—'}
                          </td>
                          <td className="px-3 py-2 tabular-nums">
                            {compareQuery.data.period_a.observations} / {compareQuery.data.period_b.observations}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                )
              })()}
            </>
          ) : (
            <p className="py-6 text-center text-sm text-slate-500">Choose both date ranges to compare.</p>
          )}
        </div>
      </section>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <section className="card overflow-hidden">
          <div className="border-b border-slate-200 px-4 py-3 text-sm font-semibold">Latest readings</div>
          {latestQuery.isLoading ? <LoadingSpinner /> : (
            <DataTable emptyMessage="No readings for this station." rows={(latestQuery.data || []).slice(0, 20)} columns={[
              { key: 'type', label: 'Type id', render: (r) => r.measurement_type_id },
              { key: 'value', label: 'Value', render: (r) => `${r.normalized_value ?? '—'} ${r.unit || ''}` },
              { key: 'time', label: 'Observed', render: (r) => new Date(r.observation_time).toLocaleString() },
              { key: 'quality', label: 'Quality', render: (r) => <StatusBadge status={r.quality_status} /> },
            ]} />
          )}
        </section>
        <section className="card overflow-hidden">
          <div className="border-b border-slate-200 px-4 py-3 text-sm font-semibold">Open quality flags</div>
          {flagsQuery.isLoading ? <LoadingSpinner /> : (
            <DataTable emptyMessage="No open flags." rows={flagsQuery.data?.data || []} columns={[
              { key: 'rule', label: 'Rule', render: (r) => r.rule_code },
              { key: 'type', label: 'Type id', render: (r) => r.measurement_type_id },
              { key: 'value', label: 'Value', render: (r) => r.original_value ?? '—' },
              { key: 'quality', label: 'Status', render: (r) => <StatusBadge status={r.quality_status} /> },
              { key: 'explanation', label: 'Explanation', render: (r) => r.explanation },
            ]} />
          )}
        </section>
      </div>
    </div>
  )
}
