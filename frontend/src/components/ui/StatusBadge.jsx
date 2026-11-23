// A small coloured pill used for station status, alert severity and quality flags.
const STYLES = {
  ONLINE: 'bg-green-100 text-green-800',
  DELAYED: 'bg-amber-100 text-amber-800',
  OFFLINE: 'bg-red-100 text-red-800',
  MAINTENANCE: 'bg-blue-100 text-blue-800',
  UNKNOWN: 'bg-slate-100 text-slate-700',
  ACTIVE: 'bg-orange-100 text-orange-800',
  ACKNOWLEDGED: 'bg-blue-100 text-blue-800',
  RESOLVED: 'bg-green-100 text-green-800',
  INFO: 'bg-slate-100 text-slate-700',
  WARNING: 'bg-amber-100 text-amber-800',
  CRITICAL: 'bg-red-100 text-red-800',
  VALID: 'bg-green-100 text-green-800',
  SUSPECT: 'bg-amber-100 text-amber-800',
  INVALID: 'bg-red-100 text-red-800',
  MISSING: 'bg-slate-200 text-slate-700',
  UNVERIFIED: 'bg-indigo-100 text-indigo-800',
}

export default function StatusBadge({ status }) {
  const style = STYLES[status] || STYLES.UNKNOWN
  return <span className={`badge ${style}`}>{status || 'UNKNOWN'}</span>
}
