import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import ErrorState from '../components/ui/ErrorState'
import ImportProgressBar from '../components/ui/ImportProgressBar'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import PageHeader from '../components/ui/PageHeader'
import { useImportProgress } from '../hooks/useImports'
import { useStations } from '../hooks/useStations'
import { extractError } from '../services/api'
import importService from '../services/importService'
import stationService from '../services/stationService'
import { findStationByName } from '../utils/stations'

/**
 * Upload page for an AWS site that does not exist yet. The file is inspected
 * first; if its metadata identifies a station that station is used, otherwise
 * one is created from the site name before the import is processed.
 */
export default function AwsUploadPage() {
  const [params] = useSearchParams()
  const siteName = params.get('name') || 'New AWS station'
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const stationsQuery = useStations({ page: 1, per_page: 100 })
  const existing = findStationByName(stationsQuery.data?.data || [], siteName)

  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [activeBatchId, setActiveBatchId] = useState(null)
  const progressQuery = useImportProgress(activeBatchId, Boolean(activeBatchId))

  if (stationsQuery.isLoading) return <LoadingSpinner label="Loading stations…" />
  if (stationsQuery.isError) {
    return (
      <ErrorState message="Could not load stations." onRetry={stationsQuery.refetch} />
    )
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (!file) return
    setBusy(true)
    setError('')
    setNotice('Inspecting file…')
    try {
      const formData = new FormData()
      formData.append('file', file)

      const batch = await importService.upload(formData)
      let stationId = batch.station_id || existing?.id

      // CSV files have no Metadata sheet, so create the station from the site
      // name and attach it to this batch before processing.
      if (!stationId) {
        setNotice('Creating station…')
        const created = await stationService.create({
          station_code:
            siteName.replace(/[^a-z0-9]/gi, '').toUpperCase().slice(0, 50) || 'AWSSTATION',
          name: siteName,
          timezone: 'Asia/Manila',
          measurement_interval_seconds: 900,
          operational_status: 'UNKNOWN',
        })
        stationId = created.id
        await importService.updateMapping(batch.id, { station_id: stationId })
      }

      setActiveBatchId(batch.id)
      setNotice('Importing readings…')
      const result = await importService.process(batch.id)

      queryClient.invalidateQueries({ queryKey: ['stations'] })
      queryClient.invalidateQueries({ queryKey: ['imports'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['measurements'] })

      setNotice(
        `Imported ${result?.summary?.imported_rows ?? 0} readings. Opening ${siteName}…`,
      )
      setTimeout(() => navigate(`/aws/${stationId}`), 1200)
    } catch (err) {
      setError(extractError(err))
      setNotice('')
      setActiveBatchId(null)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <PageHeader
        title={`Upload data — ${siteName}`}
        description="Upload an Excel or CSV file for this AWS site. Readings will appear on its own analytics page."
      />

      <section className="card max-w-2xl p-6">
        {existing && (
          <p className="mb-4 text-sm text-slate-600">
            This station already exists as{' '}
            <button
              type="button"
              className="font-medium text-brand-600 underline"
              onClick={() => navigate(`/aws/${existing.id}`)}
            >
              {existing.name} ({existing.station_code})
            </button>
            . You can still upload another file below.
          </p>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label" htmlFor="aws-upload-file">
              Source file (.xlsx, .xlsm or .csv)
            </label>
            <input
              id="aws-upload-file"
              type="file"
              accept=".xlsx,.xlsm,.csv"
              className="input"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
            />
            {file && (
              <p className="mt-2 text-xs text-slate-500">
                {file.name} — {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            )}
          </div>

          <p className="text-xs text-slate-500">
            Workbooks with a Metadata sheet provide the station code automatically.
            For CSV files, the station is created from the site name and the raw
            file is preserved for later download.
          </p>

          {activeBatchId && <ImportProgressBar progress={progressQuery.data} />}

          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}
          {notice && <p className="text-sm text-slate-600">{notice}</p>}

          <div className="flex gap-2">
            <button type="submit" className="btn-primary" disabled={busy || !file}>
              {busy ? 'Working…' : 'Upload & import'}
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => navigate(-1)}
              disabled={busy}
            >
              Cancel
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}
