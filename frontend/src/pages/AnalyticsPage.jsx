import { useMemo, useState } from 'react'
import TrendChart from '../components/charts/TrendChart'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import PageHeader from '../components/ui/PageHeader'
import SearchableSelect from '../components/ui/SearchableSelect'
import SummaryCard from '../components/ui/SummaryCard'
import { useStatistics, useTrends } from '../hooks/useMeasurements'
import { useMeasurementTypes } from '../hooks/useSensors'
import { useStations } from '../hooks/useStations'
import { extractError } from '../services/api'

const CATEGORIES = ['ATMOSPHERIC', 'WIND', 'PRECIPITATION', 'SOLAR', 'SOIL', 'EQUIPMENT']

export default function AnalyticsPage() {
  const stationsQuery = useStations({ page: 1, per_page: 100 })
  const typesQuery = useMeasurementTypes()
  const [stationId, setStationId] = useState('')
  const [typeId, setTypeId] = useState('')
  const [days, setDays] = useState(3650) // default: show all imported history
  const [interval, setInterval] = useState(60)

  const types = typesQuery.data || []
  const effectiveTypeId = typeId || types[0]?.id
  const effectiveStationId = stationId || stationsQuery.data?.data?.[0]?.id
  // Keep this stable across renders, otherwise the React Query key changes on
  // every render and the chart/statistics requests never settle.
  const dateFrom = useMemo(
    () => new Date(Date.now() - days * 86400000).toISOString(),
    [days],
  )

  const statsQuery = useStatistics({
    station_id: effectiveStationId,
    measurement_type_id: effectiveTypeId,
    date_from: dateFrom,
  })
  const trendsQuery = useTrends({
    station_id: effectiveStationId,
    measurement_type_ids: effectiveTypeId ? [Number(effectiveTypeId)] : [],
    interval_minutes: interval,
    date_from: dateFrom,
  })

  const isLoading = stationsQuery.isLoading || typesQuery.isLoading
  if (isLoading) return <LoadingSpinner label="Loading analytics…" />
  if (stationsQuery.isError || typesQuery.isError) {
    return <ErrorState message="Could not load configuration data." />
  }

  const stats = statsQuery.data

  return (
    <div>
      <PageHeader
        title="Environmental Analytics"
        description="Statistical summaries and time-series analysis for every stored measurement type."
      />

      <div className="card mb-4 flex flex-col gap-3 p-4 sm:flex-row">
        <select className="input sm:w-56" value={stationId} onChange={(event) => setStationId(event.target.value)}>
          <option value="">First available station</option>
          {(stationsQuery.data?.data || []).map((station) => (
            <option key={station.id} value={station.id}>{station.name}</option>
          ))}
        </select>
        <SearchableSelect
          className="sm:w-64"
          value={effectiveTypeId || ''}
          onChange={(value) => setTypeId(Number(value))}
          placeholder="Choose a measurement type…"
          groups={CATEGORIES.map((category) => ({
            label: category,
            options: types
              .filter((type) => type.category === category)
              .map((type) => ({
                value: type.id,
                label: type.name,
                description: type.unit,
              })),
          })).filter((group) => group.options.length > 0)}
        />
        <select className="input sm:w-40" value={days} onChange={(event) => setDays(Number(event.target.value))}>
          <option value={1}>Last 24 hours</option>
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
          <option value={365}>Last year</option>
          <option value={3650}>All dates</option>
        </select>
        <div className="sm:w-44">
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
          <SummaryCard label="Completeness" value={stats?.completeness_percent != null ? `${stats.completeness_percent}%` : '—'} hint={`${stats?.missing_records ?? 0} missing`} />
        </section>
      )}

      <section className="card mt-6 p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">
          Trend — {stats?.name || 'Select a measurement type'}
        </h2>
        {trendsQuery.isLoading ? <LoadingSpinner /> : trendsQuery.isError ? (
          <ErrorState message="Could not load trend." onRetry={trendsQuery.refetch} />
        ) : (
          <TrendChart series={trendsQuery.data || []} unit={stats?.unit} height={360} />
        )}
      </section>

      {stats?.quality_breakdown && (
        <section className="card mt-6 p-4">
          <h2 className="mb-3 text-sm font-semibold text-slate-900">Quality breakdown</h2>
          <div className="flex flex-wrap gap-3">
            {Object.entries(stats.quality_breakdown).map(([status, count]) => (
              <div key={status} className="rounded border border-slate-200 px-3 py-2 text-sm">
                <span className="font-medium">{status}</span>: {count}
              </div>
            ))}
          </div>
          {stats.circular_mean != null && (
            <p className="mt-3 text-sm text-slate-600">Circular mean direction: {stats.circular_mean}°</p>
          )}
          <p className="mt-3 text-xs text-slate-500">
            Missing records are calculated from the station interval and are never treated as zero.
          </p>
        </section>
      )}
    </div>
  )
}
