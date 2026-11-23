import { useMemo, useState } from 'react'
import {
  AlertTriangle,
  ChevronDown,
  Clock3,
  Database,
  MapPin,
  Radio,
  ShieldCheck,
  Wifi,
} from 'lucide-react'
import TrendChart from '../components/charts/TrendChart'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import PageHeader from '../components/ui/PageHeader'
import SearchableSelect from '../components/ui/SearchableSelect'
import StatusBadge from '../components/ui/StatusBadge'
import SummaryCard from '../components/ui/SummaryCard'
import {
  useDashboardSummary,
  useEnvironmentalSummary,
  useRecentAlerts,
  useStationStatus,
} from '../hooks/useDashboard'
import { useTrends } from '../hooks/useMeasurements'
import { useMeasurementTypes } from '../hooks/useSensors'
import { useStations } from '../hooks/useStations'

function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function formatValue(value, unit) {
  if (value === null || value === undefined) return '—'
  return `${Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })}${
    unit ? ` ${unit}` : ''
  }`
}

export default function DashboardPage() {
  const summary = useDashboardSummary()
  const environmental = useEnvironmentalSummary()
  const stations = useStationStatus()
  const alerts = useRecentAlerts()

  // Chart controls. Values are always fetched from the API.
  const [chartStation, setChartStation] = useState('')
  const [latestOpen, setLatestOpen] = useState(true)
  const [interval, setInterval] = useState(60)
  const [days, setDays] = useState(3650) // default: show all imported history
  const [extraTypeIds, setExtraTypeIds] = useState([])
  const typesQuery = useMeasurementTypes()
  const stationsQuery = useStations({ page: 1, per_page: 100 })

  const chartCodes = [
    'air_temperature', 'relative_humidity', 'wind_speed', 'rainfall',
    'solar_radiation', 'soil_water_content', 'battery_percentage',
  ]
  const defaultChartTypes = (typesQuery.data || []).filter((type) => chartCodes.includes(type.code))
  const extraChartTypes = (typesQuery.data || []).filter((type) => extraTypeIds.includes(type.id))
  const chartTypes = [...defaultChartTypes, ...extraChartTypes].filter(
    (type, index, all) => all.findIndex((item) => item.id === type.id) === index,
  )
  const parameterGroups = [...new Set((typesQuery.data || []).map((type) => type.category))]
    .map((category) => ({
      label: category,
      options: (typesQuery.data || [])
        .filter((type) => type.category === category && !chartTypes.some((selected) => selected.id === type.id))
        .map((type) => ({ value: type.id, label: type.name, description: type.unit })),
    }))
    .filter((group) => group.options.length > 0)
  // Prefer a station that actually has recent measurements for the overview.
  const stationWithData = (stations.data || []).find(
    (station) => station.last_observation_time,
  )
  const selectedStationId = chartStation || stationWithData?.station_id || stationsQuery.data?.data?.[0]?.id
  const dateFrom = useMemo(
    () => new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString(),
    [days],
  )
  const trendsQuery = useTrends({
    station_id: selectedStationId,
    measurement_type_ids: chartTypes.map((type) => type.id),
    interval_minutes: interval,
    date_from: dateFrom,
  })
  // Hide parameters that have no readings for the selected station and range.
  const visibleCharts = (trendsQuery.data || []).filter(
    (series) => series.points.length > 0,
  )

  const data = summary.data
  const isLoading = summary.isLoading

  return (
    <div>
      <PageHeader
        title="Monitoring Dashboard"
        description="Live overview of stations, sensors, environmental conditions and data quality."
        actions={
          <button type="button" className="btn-secondary" onClick={() => summary.refetch()}>
            Refresh data
          </button>
        }
      />

      {summary.isError ? (
        <ErrorState
          message={summary.error?.message || 'Cannot reach the API.'}
          onRetry={() => summary.refetch()}
        />
      ) : isLoading ? (
        <LoadingSpinner label="Loading dashboard summary…" />
      ) : (
        <>
          {/* A. Summary cards — every value comes from /dashboard/summary */}
          <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            <SummaryCard label="Total stations" value={data?.total_stations} icon={MapPin} />
            <SummaryCard label="Online" value={data?.online_stations} tone="green" icon={Wifi} />
            <SummaryCard label="Delayed" value={data?.delayed_stations} tone="amber" icon={Clock3} />
            <SummaryCard label="Offline" value={data?.offline_stations} tone="red" icon={Radio} />
            <SummaryCard
              label="Under maintenance"
              value={data?.maintenance_stations}
              tone="blue"
              icon={ShieldCheck}
            />
            <SummaryCard label="Registered sensors" value={data?.total_sensors} icon={Radio} />
            <SummaryCard label="Active alerts" value={data?.active_alerts} tone="red" icon={AlertTriangle} />
            <SummaryCard
              label="Quality warnings"
              value={data?.data_quality_warnings}
              tone="amber"
              icon={ShieldCheck}
            />
            <SummaryCard
              label="Latest import"
              value={
                data?.latest_import_at
                  ? new Date(data.latest_import_at).toLocaleDateString()
                  : 'Never'
              }
              hint={data?.latest_import_at ? formatDateTime(data.latest_import_at) : 'No files imported yet'}
              tone="slate"
              icon={Database}
            />
          </section>

          {/* B. Latest measurements */}
          <section className="card mt-6 overflow-hidden">
            <button
              type="button"
              onClick={() => setLatestOpen((open) => !open)}
              className="flex w-full items-center justify-between border-b border-slate-200 px-4 py-3 text-left hover:bg-slate-50"
              aria-expanded={latestOpen}
            >
              <span>
                <span className="block text-sm font-semibold text-slate-900">
                  Latest Environmental Measurements
                </span>
                <span className="block text-xs text-slate-500">
                  Each row shows the station and observation time for that reading.
                </span>
              </span>
              <span className="flex items-center gap-2 text-xs text-slate-500">
                {environmental.data?.length ? `${environmental.data.length} parameters` : ''}
                <ChevronDown
                  size={18}
                  className={`transition-transform ${latestOpen ? 'rotate-180' : ''}`}
                />
              </span>
            </button>
            {latestOpen && (
              <>
                {environmental.isLoading ? (
                  <LoadingSpinner label="Loading measurements…" />
                ) : environmental.isError ? (
                  <ErrorState message="Could not load measurements." onRetry={environmental.refetch} />
                ) : environmental.data?.length ? (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-slate-200 text-sm">
                      <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                        <tr>
                          <th className="px-4 py-2">Parameter</th>
                          <th className="px-4 py-2">Value</th>
                          <th className="px-4 py-2">Station</th>
                          <th className="px-4 py-2">Observed at</th>
                          <th className="px-4 py-2">Quality</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {environmental.data.map((item, index) => (
                          <tr key={`${item.measurement_type_code}-${index}`} className="hover:bg-slate-50">
                            <td className="px-4 py-2 font-medium text-slate-800">
                              {item.measurement_type_name || item.measurement_type_code}
                            </td>
                            <td className="px-4 py-2 tabular-nums">
                              {formatValue(item.value, item.unit)}
                            </td>
                            <td className="px-4 py-2">
                              {item.station_name ? `${item.station_name} (${item.station_code})` : '—'}
                            </td>
                            <td className="px-4 py-2 text-slate-600">{formatDateTime(item.observation_time)}</td>
                            <td className="px-4 py-2"><StatusBadge status={item.quality_status} /></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="p-4">
                    <EmptyState
                      title="No measurements yet"
                      description="Import an Excel or CSV file (Phase 3) to populate this table."
                    />
                  </div>
                )}
              </>
            )}
          </section>

          {/* C. Environmental trend charts */}
          <section className="card mt-6 p-4">
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-sm font-semibold text-slate-900">Environmental Trends</h2>
                <p className="text-xs text-slate-500">Chart data is aggregated by the backend from stored measurements.</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <div className="w-44">
                  <SearchableSelect
                    value={chartStation}
                    onChange={(value) => setChartStation(String(value))}
                    placeholder="First available station"
                    groups={[{
                      label: 'Stations',
                      options: (stationsQuery.data?.data || []).map((station) => ({
                        value: station.id,
                        label: station.name,
                        description: station.station_code,
                      })),
                    }]}
                  />
                </div>
                <select className="input py-1 text-xs" value={days} onChange={(event) => setDays(Number(event.target.value))}>
                  <option value={1}>Last 24 hours</option>
                  <option value={7}>Last 7 days</option>
                  <option value={30}>Last 30 days</option>
                  <option value={365}>Last year</option>
                  <option value={3650}>All dates</option>
                </select>
                <div className="w-36">
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
                <div className="w-48">
                  <SearchableSelect
                    value=""
                    onChange={(value) => setExtraTypeIds((current) => [...current, Number(value)])}
                    placeholder="+ Add parameter"
                    groups={parameterGroups}
                  />
                </div>
              </div>
              {extraChartTypes.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {extraChartTypes.map((type) => (
                    <button key={type.id} type="button"
                      onClick={() => setExtraTypeIds((current) => current.filter((id) => id !== type.id))}
                      className="badge bg-brand-50 text-brand-700 hover:bg-brand-100">
                      {type.name} ×
                    </button>
                  ))}
                </div>
              )}
            </div>

            {trendsQuery.isLoading ? (
              <LoadingSpinner label="Loading trends…" />
            ) : trendsQuery.isError ? (
              <ErrorState message="Could not load chart data." onRetry={trendsQuery.refetch} />
            ) : visibleCharts.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-300 px-4 py-10 text-center">
                <p className="text-sm font-medium text-slate-700">
                  No measurements for this station and date range
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Try “All dates”, choose another station, or import more data.
                </p>
              </div>
            ) : (
              <>
                <p className="mb-3 text-xs text-slate-500">
                  Showing {visibleCharts.length} parameter{visibleCharts.length === 1 ? '' : 's'} with data.
                  {' '}Charts without readings are hidden.
                </p>
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {visibleCharts.map((series) => (
                    <div key={series.measurement_type_id} className="rounded border border-slate-200 p-2">
                      <TrendChart title={series.name} unit={series.unit} series={[series]} height={220} />
                    </div>
                  ))}
                </div>
              </>
            )}
          </section>

          {/* D. Station status + recent alerts */}
          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <section className="card overflow-hidden">
              <div className="border-b border-slate-200 px-4 py-3">
                <h2 className="text-sm font-semibold text-slate-900">Station Status</h2>
              </div>
              {stations.data?.length ? (
                <div className="divide-y divide-slate-100">
                  {stations.data.map((station) => (
                    <div key={station.station_id} className="flex items-center justify-between gap-3 px-4 py-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-slate-800">
                          {station.station_name}
                        </p>
                        <p className="text-xs text-slate-500">
                          Last observation: {formatDateTime(station.last_observation_time)}
                        </p>
                      </div>
                      <StatusBadge status={station.operational_status} />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-4"><EmptyState title="No stations registered" /></div>
              )}
            </section>

            <section className="card overflow-hidden">
              <div className="border-b border-slate-200 px-4 py-3">
                <h2 className="text-sm font-semibold text-slate-900">Recent Alerts</h2>
              </div>
              {alerts.data?.length ? (
                <div className="divide-y divide-slate-100">
                  {alerts.data.map((alert) => (
                    <div key={alert.id} className="flex items-start justify-between gap-3 px-4 py-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-slate-800">{alert.title}</p>
                        <p className="text-xs text-slate-500">{formatDateTime(alert.created_at)}</p>
                      </div>
                      <StatusBadge status={alert.severity} />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-4"><EmptyState title="No alerts" /></div>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  )
}
