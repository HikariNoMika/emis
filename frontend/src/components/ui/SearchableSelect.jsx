import { useEffect, useMemo, useRef, useState } from 'react'
import { Check, ChevronDown, Search } from 'lucide-react'

/**
 * A searchable dropdown with grouped options.
 *
 * `groups` is an array of { label, options: [{ value, label, description }] }.
 * It is a plain button + panel (no native select) so it can be styled
 * consistently and can show extra detail such as units.
 */
export default function SearchableSelect({
  value,
  onChange,
  groups = [],
  placeholder = 'Select…',
  className = '',
}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const containerRef = useRef(null)

  const flat = useMemo(
    () => groups.flatMap((group) => group.options || []),
    [groups],
  )
  const selected = flat.find((option) => String(option.value) === String(value))

  // Close when clicking outside or pressing Escape.
  useEffect(() => {
    const handlePointer = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setOpen(false)
      }
    }
    const handleKey = (event) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', handlePointer)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handlePointer)
      document.removeEventListener('keydown', handleKey)
    }
  }, [])

  const filteredGroups = groups
    .map((group) => ({
      ...group,
      options: (group.options || []).filter((option) =>
        `${option.label} ${option.description || ''} ${group.label || ''}`
          .toLowerCase()
          .includes(query.toLowerCase()),
      ),
    }))
    .filter((group) => group.options.length > 0)

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => { setOpen((current) => !current); setQuery('') }}
        className="flex w-full items-center justify-between gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-left text-sm shadow-sm transition hover:border-brand-500 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="min-w-0 truncate">
          {selected ? (
            <>
              <span className="font-medium text-slate-800">{selected.label}</span>
              {selected.description && (
                <span className="ml-1 text-xs text-slate-500">({selected.description})</span>
              )}
            </>
          ) : (
            <span className="text-slate-500">{placeholder}</span>
          )}
        </span>
        <ChevronDown
          size={16}
          className={`shrink-0 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div className="absolute z-30 mt-1 w-full min-w-[16rem] overflow-hidden rounded-md border border-slate-200 bg-white shadow-lg">
          <div className="flex items-center gap-2 border-b border-slate-100 px-3 py-2">
            <Search size={15} className="shrink-0 text-slate-400" />
            <input
              autoFocus
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search parameters…"
              className="w-full border-0 bg-transparent text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none"
            />
          </div>
          <div className="max-h-64 overflow-y-auto py-1" role="listbox">
            {filteredGroups.length === 0 && (
              <p className="px-3 py-3 text-sm text-slate-500">No matches found.</p>
            )}
            {filteredGroups.map((group) => (
              <div key={group.label || 'options'}>
                {group.label && (
                  <p className="px-3 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                    {group.label}
                  </p>
                )}
                {group.options.map((option) => {
                  const active = String(option.value) === String(value)
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => { onChange(option.value); setOpen(false) }}
                      className={`flex w-full items-center justify-between gap-2 px-3 py-1.5 text-left text-sm transition ${
                        active ? 'bg-brand-50 text-brand-700' : 'text-slate-700 hover:bg-slate-50'
                      }`}
                      role="option"
                      aria-selected={active}
                    >
                      <span className="min-w-0 truncate">{option.label}</span>
                      <span className="flex shrink-0 items-center gap-2">
                        {option.description && (
                          <span className="text-[11px] text-slate-400">{option.description}</span>
                        )}
                        {active && <Check size={14} className="text-brand-600" />}
                      </span>
                    </button>
                  )
                })}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
