import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <p className="text-5xl font-bold text-brand-600">404</p>
      <h1 className="mt-3 text-xl font-semibold text-slate-900">Page not found</h1>
      <p className="mt-1 text-sm text-slate-600">
        The page you requested does not exist in this application.
      </p>
      <Link to="/" className="btn-primary mt-5">Back to dashboard</Link>
    </div>
  )
}
