export default function SummaryCard({ label, value, hint, tone = 'brand', icon: Icon }) {
  const tones = {
    brand: 'text-brand-600 bg-brand-50',
    green: 'text-green-600 bg-green-50',
    amber: 'text-amber-600 bg-amber-50',
    red: 'text-red-600 bg-red-50',
    blue: 'text-blue-600 bg-blue-50',
    slate: 'text-slate-600 bg-slate-100',
  }

  return (
    <div className="card flex items-start justify-between gap-3 p-4">
      <div className="min-w-0">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
          {label}
        </p>
        <p className="mt-1 truncate text-2xl font-semibold text-slate-900">
          {value ?? '—'}
        </p>
        {hint && <p className="mt-1 truncate text-xs text-slate-500">{hint}</p>}
      </div>
      {Icon && (
        <div className={`rounded-md p-2 ${tones[tone] || tones.brand}`}>
          <Icon size={20} />
        </div>
      )}
    </div>
  )
}
