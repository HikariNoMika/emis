import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import PageHeader from '../components/ui/PageHeader'
import { useSystemSettings } from '../hooks/useAdministration'
import { extractError } from '../services/api'
import dashboardService from '../services/dashboardService'

export default function SystemSettingsPage() {
  const queryClient = useQueryClient()
  const query = useSystemSettings()
  const [selectedKey, setSelectedKey] = useState('')
  const [text, setText] = useState('')
  const [notice, setNotice] = useState('')
  const [parseError, setParseError] = useState('')

  useEffect(() => {
    if (!selectedKey && query.data) {
      const firstKey = Object.keys(query.data)[0] || ''
      setSelectedKey(firstKey)
      setText(firstKey ? JSON.stringify(query.data[firstKey], null, 2) : '')
    }
  }, [query.data, selectedKey])

  const mutation = useMutation({
    mutationFn: (payload) => dashboardService.saveSetting(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system', 'settings'] })
      queryClient.invalidateQueries({ queryKey: ['audit-logs'] })
      setNotice('Setting saved.')
    },
  })

  const chooseKey = (key) => {
    setSelectedKey(key)
    setText(JSON.stringify(query.data[key], null, 2))
    setParseError('')
    setNotice('')
  }

  const save = () => {
    try {
      const value = JSON.parse(text)
      setParseError('')
      mutation.mutate({ key: selectedKey, value })
    } catch (error) {
      setParseError(`Invalid JSON: ${error.message}`)
    }
  }

  return (
    <div>
      <PageHeader
        title="System Settings"
        description="Configurable thresholds, quality rules, import behavior and report defaults."
      />

      {notice && <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-800">{notice}</div>}

      {/* Dedicated toggle for the first-login MFA feature (testing phase). */}
      {!query.isLoading && !query.isError && (
        <div className="card mb-6 flex flex-wrap items-center justify-between gap-4 p-5">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Enforce MFA on first login</h2>
            <p className="mt-1 max-w-xl text-xs text-slate-500">
              When ON, a user's first password change automatically sets up MFA, emails the
              authenticator secret, and requires a 6-digit code on subsequent logins.
              Leave OFF while testing.
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={Boolean(query.data?.enforce_mfa_on_first_login?.enabled)}
            onClick={() => {
              const current = Boolean(query.data?.enforce_mfa_on_first_login?.enabled)
              mutation.mutate({
                key: 'enforce_mfa_on_first_login',
                value: { enabled: !current },
              })
            }}
            disabled={mutation.isPending}
            className={`relative inline-flex h-7 w-12 shrink-0 items-center rounded-full transition ${
              query.data?.enforce_mfa_on_first_login?.enabled ? 'bg-brand-600' : 'bg-slate-300'
            }`}
          >
            <span
              className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition ${
                query.data?.enforce_mfa_on_first_login?.enabled ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      )}

      {query.isLoading ? <LoadingSpinner /> : query.isError ? (
        <ErrorState message={extractError(query.error)} onRetry={query.refetch} />
      ) : (
        <div className="grid gap-4 md:grid-cols-[260px_1fr]">
          <div className="card overflow-hidden">
            <p className="border-b border-slate-200 px-4 py-3 text-xs font-semibold uppercase text-slate-500">Settings</p>
            {Object.keys(query.data || {}).length === 0 ? (
              <p className="px-4 py-4 text-sm text-slate-500">No settings found. Run the seed script.</p>
            ) : (
              <div className="divide-y divide-slate-100">
                {Object.keys(query.data).map((key) => (
                  <button key={key} type="button" onClick={() => chooseKey(key)}
                    className={`block w-full px-4 py-3 text-left text-sm hover:bg-slate-50 ${
                      selectedKey === key ? 'bg-brand-50 text-brand-700' : 'text-slate-700'
                    }`}>
                    {key.replaceAll('_', ' ')}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="card p-5">
            <h2 className="mb-1 text-base font-semibold text-slate-900">
              {selectedKey ? selectedKey.replaceAll('_', ' ') : 'Select a setting'}
            </h2>
            <p className="mb-4 text-xs text-slate-500">Values are stored as JSON. Changes are recorded in the audit log.</p>
            <textarea className="input font-mono text-xs" rows="16" value={text}
              onChange={(event) => setText(event.target.value)} disabled={!selectedKey} />
            {parseError && <p className="mt-2 text-sm text-red-600">{parseError}</p>}
            {mutation.isError && <p className="mt-2 text-sm text-red-600">{extractError(mutation.error)}</p>}
            <div className="mt-4 flex justify-end">
              <button type="button" className="btn-primary" disabled={!selectedKey || mutation.isPending} onClick={save}>
                {mutation.isPending ? 'Saving…' : 'Save setting'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
