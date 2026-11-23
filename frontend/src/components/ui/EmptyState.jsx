export default function EmptyState({ title = 'No data available', description }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-2xl text-slate-400">
        ◌
      </div>
      <h3 className="text-sm font-semibold text-slate-700">{title}</h3>
      {description && <p className="mt-1 max-w-sm text-sm text-slate-500">{description}</p>}
    </div>
  )
}
