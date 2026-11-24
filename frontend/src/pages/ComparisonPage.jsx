import { useMemo, useState } from 'react'
import TrendChart from '../components/charts/TrendChart'
import DataTable from '../components/ui/DataTable'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import PageHeader from '../components/ui/PageHeader'
import { useComparison } from '../hooks/useMeasurements'
import { useMeasurementTypes } from '../hooks/useSensors'
import { useStations } from '../hooks/useStations'
import { extractError } from '../services/api'

export default function ComparisonPage() {
  const stationsQuery = useStations({ page: 1, per_page: 100 })
  const typesQuery = useMeasurementTypes()
  const [selectedStations, setSelectedStations] = useState([])
  const [typeId, setTypeId] = useState('')
  const [days, setDays] = useState(3650) // default: show all imported history
  const [range, setRange] = useState({ from: '', to: '' })

  const types = typesQuery.data || []
  const effectiveTypeId = typeId || types[0]?.id
  const dateFrom = useMemo(
    () => new Date(Date.now() - days * 86400000).toISOString(),
    [days],
  )

  const stationName = (id) =>
    (stationsQuery.data?.data || []).find((station) => station.id === id)?.name ||
    `Station ${id}`

  const query = useComparison({
    station_ids: selectedStations.map(Number),
    measurement_type_id: effectiveTypeId,
    date_from: range.from || dateFrom,
    ...(range.to ? { date_to: range.to } : {}),
    interval_minutes: 60,
  })

  const toggleStation = (id) => {
    setSelectedStations((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    )
  }

  const series = (query.data?.stations || []).map((item) => ({
    code: stationName(item.station_id),
    name: stationName(item.station_id),
    points: item.series,
  }))

  const columns = [
    {
      key: 'station', label: 'Station',
      render: (row) => (
        <div>
          <span className="font-medium text-slate-800">{stationName(row.station_id)}</span>
          <span className="block text-xs text-slate-500">
            {(stationsQuery.data?.data || []).find((s) => s.id === row.station_id)?.station_code || ''}
          </span>
        </div>
      ),
    },
    { key: 'observations', label: 'Observations', render: (row) => row.statistics.observations },
    { key: 'min', label: 'Min', render: (row) => row.statistics.min ?? '—' },
    { key: 'max', label: 'Max', render: (row) => row.statistics.max ?? '—' },
    { key: 'average', label: 'Average', render: (row) => row.statistics.average ?? '—' },
    { key: 'completeness', label: 'Completeness', render: (row) => row.statistics.completeness_percent != null ? `${row.statistics.completeness_percent}%` : '—' },
  ]

  if (stationsQuery.isLoading || typesQuery.isLoading) return <LoadingSpinner />

  return (
    <div>
      <PageHeader
        title="Station Comparison"
        description="Compare one compatible measurement type across multiple stations over the same period."
      />

      <div className="card mb-4 space-y-4 p-4">
        <div>
          <p className="label">Stations to compare</p>
          <div className="flex flex-wrap gap-2">
            {(stationsQuery.data?.data || []).map((station) => (
              <label key={station.id} className="flex items-center gap-2 rounded border border-slate-200 px-3 py-1.5 text-sm">
                <input type="checkbox" checked={selectedStations.includes(station.id)}
                  onChange={() => toggleStation(station.id)} />
                {station.name}
              </label>
            ))}
          </div>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <select className="input sm:w-64" value={effectiveTypeId || ''} onChange={(event) => setTypeId(Number(event.target.value))}>
            {types.map((type) => (
              <option key={type.id} value={type.id}>{type.name} ({type.unit})</option>
            ))}
          </select>
          <select className="input-compact" value={days} title="Quick range"
            onChange={(event) => { setDays(Number(event.target.value)); setRange({ from: '', to: '' }) }}>
            <option value={1}>Last 24 hours</option>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={365}>Last year</option>
            <option value={3650}>All dates</option>
          </select>
          <input type="date" className="input sm:w-40" title="Range from"
            value={range.from}
            onChange={(event) => setRange({ ...range, from: event.target.value })} />
          <input type="date" className="input sm:w-40" title="Range to"
            value={range.to}
            onChange={(event) => setRange({ ...range, to: event.target.value })} />
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Comparing {range.from || 'all dates'}{range.to ? ` to ${range.to}` : ''}. Use the date pickers for an exact range, or the quick range for a preset.
        </p>
      </div>

      {selectedStations.length < 2 ? (
        <div className="rounded-md border border-slate-200 bg-white px-4 py-10 text-center text-sm text-slate-500">
          Select at least two stations to compare.
        </div>
      ) : query.isLoading ? (
        <LoadingSpinner />
      ) : query.isError ? (
        <ErrorState message={extractError(query.error)} onRetry={query.refetch} />
      ) : (
        <>
          <section className="card p-4">
            <TrendChart series={series} unit={types.find((type) => type.id === effectiveTypeId)?.unit} height={360} />
          </section>
          <section className="card mt-6 overflow-hidden">
            <DataTable rows={query.data?.stations || []} columns={columns} keyField="station_id" emptyMessage="No comparable data." />
          </section>
          <p className="mt-3 text-xs text-slate-500">
            Only the same measurement type and unit are compared. Missing readings are excluded, never counted as zero.
          </p>
        </>
      )}

    </div>
  )
}
