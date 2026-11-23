export default function ErrorState({ message, onRetry }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-6 py-10 text-center">
      <h3 className="text-sm font-semibold text-red-800">Unable to load data</h3>
      <p className="mt-1 text-sm text-red-700">{message}</p>
      {onRetry && (
        <button type="button" className="btn-secondary mt-4" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}
