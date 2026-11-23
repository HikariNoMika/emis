export default function Pagination({ meta, onPageChange }) {
  if (!meta || meta.total_pages <= 1) return null
  return (
    <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-xs text-slate-600">
      <span>
        Page {meta.page} of {meta.total_pages} · {meta.total} records
      </span>
      <div className="flex gap-2">
        <button
          type="button"
          className="btn-secondary disabled:opacity-40"
          disabled={!meta.has_prev}
          onClick={() => onPageChange(meta.page - 1)}
        >
          Previous
        </button>
        <button
          type="button"
          className="btn-secondary disabled:opacity-40"
          disabled={!meta.has_next}
          onClick={() => onPageChange(meta.page + 1)}
        >
          Next
        </button>
      </div>
    </div>
  )
}
