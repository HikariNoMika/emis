import EmptyState from './EmptyState'

/**
 * Generic table used by list pages.
 * `columns` entries: { key, label, render: (row) => JSX, className }
 */
export default function DataTable({ columns, rows, keyField = 'id', emptyMessage }) {
  if (!rows || rows.length === 0) {
    return <EmptyState title={emptyMessage || 'No records found'} />
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
          <tr>
            {columns.map((column) => (
              <th key={column.key} className={`px-4 py-2 ${column.className || ''}`}>
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((row) => (
            <tr key={row[keyField]} className="hover:bg-slate-50">
              {columns.map((column) => (
                <td key={column.key} className={`px-4 py-2 ${column.className || ''}`}>
                  {column.render ? column.render(row) : row[column.key] ?? '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
