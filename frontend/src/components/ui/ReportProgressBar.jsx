/** Live progress for a running report generation (polled while in flight). */
export default function ReportProgressBar({ progress }) {
  if (!progress) {
    return (
      <div className="rounded-md border border-brand-100 bg-brand-50 p-4 text-sm text-brand-900">
        Starting report…
      </div>
    )
  }
  const percent = progress.percent ?? 0
  const finished = progress.status === 'COMPLETED' || progress.status === 'FAILED'

  return (
    <div className="rounded-md border border-brand-100 bg-brand-50 p-4">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium text-brand-900">
          {progress.message || 'Generating report…'}
        </span>
        <span className="shrink-0 font-semibold text-brand-800">{percent}%</span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-brand-100">
        <div
          className={`h-full transition-all duration-500 ${
            progress.status === 'FAILED' ? 'bg-red-500' : 'bg-brand-600'
          }`}
          style={{ width: `${percent}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-brand-800/70">
        {finished ? 'Finished' : 'Working'} · step {progress.step ?? 0} of{' '}
        {progress.total_steps ?? 0}
      </p>
    </div>
  )
}
