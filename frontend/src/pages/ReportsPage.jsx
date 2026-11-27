import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import DataTable from '../components/ui/DataTable'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import PageHeader from '../components/ui/PageHeader'
import Pagination from '../components/ui/Pagination'
import { useMeasurementTypes } from '../hooks/useSensors'
import { useReports } from '../hooks/useAdministration'
import { useStations } from '../hooks/useStations'
import { extractError } from '../services/api'
import reportService from '../services/reportService'

const REPORT_TYPES = [
  ['daily', 'Daily environmental report'],
  ['weekly', 'Weekly environmental report'],
  ['monthly', 'Monthly environmental report'],
  ['station_performance', 'Station performance report'],
  ['sensor_health', 'Sensor health report'],
  ['data_quality', 'Data quality report'],
  ['rainfall', 'Rainfall report'],
  ['environmental_trends', 'Environmental trend report'],
  ['multi_station_comparison', 'Multi-station comparison report'],
  ['import_summary', 'Data import summary'],
  ['maintenance_calibration', 'Maintenance and calibration report'],
  ['station_full', 'Station comprehensive report (trends + gaps)'],
  ['station_comparison', '3-station comparison (trends + table + lows/highs)'],
  ['quarterly_analysis', 'Quarterly Data Analysis Report (Word)'],
]

export default function ReportsPage() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [reportType, setReportType] = useState('daily')
  const [stationId, setStationId] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [format, setFormat] = useState('pdf')
  const [reportingYear, setReportingYear] = useState(new Date().getFullYear())
  const [quarter, setQuarter] = useState(1)
  const [selectedTypes, setSelectedTypes] = useState([])
  const [selectedStations, setSelectedStations] = useState([])
  const [notice, setNotice] = useState('')

  const query = useReports({ page, per_page: 15 })
  const stationsQuery = useStations({ page: 1, per_page: 100 })
  const typesQuery = useMeasurementTypes()

  const mutation = useMutation({
    mutationFn: (payload) => reportService.generate(payload),
    onSuccess: (report) => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
      queryClient.invalidateQueries({ queryKey: ['audit-logs'] })
      setNotice(`Report ${report.report_number} generated. Use Download to save the file.`)
    },
  })

  const generate = (event) => {
    event.preventDefault()
    mutation.mutate({
      report_type: reportType,
      station_id: stationId ? Number(stationId) : null,
      date_from: dateFrom || null,
      date_to: dateTo || null,
      file_format: reportType === 'quarterly_analysis' ? 'docx' : format,
      measurement_type_ids: selectedTypes.map(Number),
      station_ids: selectedStations.map(Number),
      reporting_year: Number(reportingYear),
      quarter: Number(quarter),
    })
  }

  const columns = [
    { key: 'number', label: 'Report', render: (row) => <span className="font-medium">{row.report_number}</span> },
    { key: 'title', label: 'Title', render: (row) => row.title },
    { key: 'type', label: 'Type', render: (row) => row.report_type },
    { key: 'station', label: 'Station', render: (row) => row.station_name || 'All stations' },
    { key: 'generated', label: 'Generated', render: (row) => new Date(row.generated_at).toLocaleString() },
    { key: 'format', label: 'Format', render: (row) => row.file_format.toUpperCase() },
    {
      key: 'download', label: 'Download',
      render: (row) => (
        <button type="button" className="text-xs font-medium text-brand-600 hover:underline"
          onClick={() => reportService.download(row.id, row.file_name).catch((error) => setNotice(extractError(error)))}>
          Download {row.file_format.toUpperCase()}
        </button>
      ),
    },
  ]

  return (
    <div>
      <PageHeader title="Reports" description="Generate PDF, Excel and Word reports from stored monitoring data." />

      {notice && <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-800">{notice}</div>}

      <div className="card mb-6 p-5">
        <h2 className="mb-4 text-sm font-semibold text-slate-900">Generate a report</h2>
        <form onSubmit={generate} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <label className="label">Report type</label>
              <select className="input" value={reportType} onChange={(event) => setReportType(event.target.value)}>
                {REPORT_TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </div>
            {reportType === 'quarterly_analysis' ? (
              <>
                <div>
                  <label className="label">Reporting year</label>
                  <select className="input" value={reportingYear} onChange={(event) => setReportingYear(Number(event.target.value))}>
                    {[2026, 2025, 2024, 2023].map((year) => <option key={year} value={year}>{year}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">Quarter</label>
                  <select className="input" value={quarter} onChange={(event) => setQuarter(Number(event.target.value))}>
                    {[1, 2, 3, 4].map((value) => <option key={value} value={value}>Q{value}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">Format</label>
                  <input className="input bg-slate-50" value="Word (.docx)" disabled readOnly />
                </div>
              </>
            ) : (
              <>
                {reportType !== 'station_comparison' && (
                  <div>
                    <label className="label">Station</label>
                    <select className="input" value={stationId} onChange={(event) => setStationId(event.target.value)}>
                      <option value="">All stations</option>
                      {(stationsQuery.data?.data || []).map((station) => (
                        <option key={station.id} value={station.id}>
                          {station.name} ({station.station_code})
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                <div>
                  <label className="label">Format</label>
                  <select className="input" value={format} onChange={(event) => setFormat(event.target.value)}>
                    <option value="pdf">PDF</option>
                    <option value="xlsx">Excel (.xlsx)</option>
                  </select>
                </div>
                <div>
                  <label className="label">Date from</label>
                  <input className="input" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
                </div>
                <div>
                  <label className="label">Date to</label>
                  <input className="input" type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
                </div>
              </>
            )}
          </div>

          {reportType !== 'quarterly_analysis' && (
          <div>
            <p className="label">Measurement types (leave empty for all)</p>
            <div className="flex flex-wrap gap-2">
              {(typesQuery.data || []).map((type) => (
                <label key={type.id} className="flex items-center gap-1 rounded border border-slate-200 px-2 py-1 text-xs">
                  <input type="checkbox" checked={selectedTypes.includes(type.id)}
                    onChange={() => setSelectedTypes((current) =>
                      current.includes(type.id)
                        ? current.filter((item) => item !== type.id)
                        : [...current, type.id],
                    )} />
                  {type.name}
                </label>
              ))}
            </div>
          </div>
          )}

          {reportType === 'station_comparison' && (
            <div>
              <p className="label">Stations to compare (up to 3)</p>
              <div className="flex flex-wrap gap-2">
                {(stationsQuery.data?.data || []).map((station) => (
                  <label key={station.id} className="flex items-center gap-1 rounded border border-slate-200 px-2 py-1 text-xs">
                    <input
                      type="checkbox"
                      checked={selectedStations.includes(station.id)}
                      onChange={() => setSelectedStations((current) =>
                        current.includes(station.id)
                          ? current.filter((id) => id !== station.id)
                          : current.length < 3 ? [...current, station.id] : current,
                      )}
                    />
                    {station.name} <span className="text-slate-400">({station.station_code})</span>
                  </label>
                ))}
              </div>
              <p className="mt-1 text-xs text-slate-500">
                Pick up to 3 stations. Each parameter gets an overlaid trend chart, a comparison table and its recorded low/high.
              </p>
            </div>
          )}

          <div className="flex justify-end">
            <button type="submit" className="btn-primary" disabled={mutation.isPending}>
              {mutation.isPending ? 'Generating…' : 'Generate report'}
            </button>
          </div>
          {mutation.isError && <p className="text-sm text-red-600">{extractError(mutation.error)}</p>}
        </form>
      </div>

      <div className="card overflow-hidden">
        <div className="border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-900">Generation history</h2>
        </div>
        {query.isLoading ? <LoadingSpinner /> : query.isError ? (
          <ErrorState message={extractError(query.error)} onRetry={query.refetch} />
        ) : (
          <>
            <DataTable rows={query.data?.data || []} columns={columns} emptyMessage="No reports generated yet." />
            <Pagination meta={query.data?.meta} onPageChange={setPage} />
          </>
        )}
      </div>

      <p className="mt-3 text-xs text-slate-500">
        Every report includes station information, reporting period, measurement units,
        statistical summaries, data source, generation date and data quality notes.
      </p>
    </div>
  )
}
