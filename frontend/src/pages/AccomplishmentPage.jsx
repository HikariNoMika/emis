import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import DataTable from '../components/ui/DataTable'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import Modal from '../components/ui/Modal'
import PageHeader from '../components/ui/PageHeader'
import StatusBadge from '../components/ui/StatusBadge'
import SummaryCard from '../components/ui/SummaryCard'
import {
  useAccomplishmentActuals,
  useAccomplishmentIndicators,
  useAccomplishmentReports,
  useAccomplishmentSummary,
  useAccomplishmentTargets,
  useAccomplishmentWeights,
  useDataCompleteness,
} from '../hooks/useAccomplishment'
import { extractError } from '../services/api'
import accomplishmentService from '../services/accomplishmentService'

const SECTIONS = [
  ['dashboard', 'Dashboard'],
  ['indicators', 'Indicators'],
  ['targets', 'Quarterly targets'],
  ['actuals', 'Actual accomplishments'],
  ['weights', 'Weights'],
  ['annual', 'Annual summary'],
  ['reports', 'Report generation'],
]

const UNITS = [
  'Number of activities', 'Number of inspections', 'Number of stations',
  'Number of reports', 'Number of datasets', 'Number of equipment units',
  'Percentage', 'Other',
]

function currentYear() {
  return new Date().getFullYear()
}

function pct(value) {
  return value === null || value === undefined ? 'N/A' : `${Number(value).toFixed(2)}%`
}

function SectionTabs({ section, setSection }) {
  return (
    <div className="mb-5 flex flex-wrap gap-2">
      {SECTIONS.map(([key, label]) => (
        <button
          key={key}
          type="button"
          onClick={() => setSection(key)}
          className={`rounded-md px-3 py-1.5 text-sm font-medium ${
            section === key ? 'bg-brand-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-100'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

function DashboardSection({ year, quarter }) {
  const query = useAccomplishmentSummary(year, quarter)
  const data = query.data

  if (query.isLoading) return <LoadingSpinner label="Calculating accomplishment…" />
  if (query.isError) return <ErrorState message={extractError(query.error)} onRetry={query.refetch} />

  const detail = quarter ? data : data?.quarters?.Q1
  const categories = detail?.categories || {}

  return (
    <div className="space-y-5">
      {!quarter && (
        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {Object.entries(data?.quarters || {}).map(([key, item]) => (
            <div key={key} className="card p-4">
              <p className="text-xs font-semibold uppercase text-slate-500">{key} {year}</p>
              <p className="mt-1 text-2xl font-semibold text-brand-700">{pct(item.overall)}</p>
              <p className="mt-1 text-xs text-slate-500">
                Activities {pct(item.categories?.ACTIVITY?.score)} · Deliverables {pct(item.categories?.DELIVERABLE?.score)}
              </p>
              <div className="mt-2 flex flex-wrap gap-1 text-[11px] text-slate-500">
                <span>Completed {item.counts?.completed}</span>
                <span>· Ongoing {item.counts?.ongoing}</span>
                <span>· Delayed {item.counts?.delayed}</span>
                <span>· Unconfigured {item.counts?.unconfigured}</span>
              </div>
              {!item.is_complete && (
                <span className="badge mt-2 bg-amber-100 text-amber-800">PRELIMINARY</span>
              )}
            </div>
          ))}
        </section>
      )}

      <section className="grid gap-3 sm:grid-cols-3">
        <SummaryCard label="Activities score" value={pct(categories.ACTIVITY?.score)} hint={`Weight ${categories.ACTIVITY?.weight ?? '—'}%`} />
        <SummaryCard label="Deliverables score" value={pct(categories.DELIVERABLE?.score)} hint={`Weight ${categories.DELIVERABLE?.weight ?? '—'}%`} />
        <SummaryCard label="Overall accomplishment" value={pct(detail?.overall)} tone="brand" />
      </section>

      {!detail?.is_complete && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {detail?.remarks?.join(' ') || 'Scores are preliminary because indicators or weights are incomplete.'}
        </div>
      )}

      <section className="card overflow-hidden">
        <div className="border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-900">Indicator detail</h2>
        </div>
        <DataTable
          emptyMessage="No indicators configured for this year."
          keyField="id"
          columns={[
            { key: 'name', label: 'Indicator', render: (r) => r.name },
            { key: 'category', label: 'Category', render: (r) => r.category },
            { key: 'planned_target', label: 'Planned', render: (r) => r.planned_target ?? 'N/A' },
            { key: 'actual', label: 'Actual', render: (r) => r.actual_accomplishment ?? '—' },
            { key: 'unit', label: 'Unit', render: (r) => r.unit },
            { key: 'percentage', label: 'Accomplishment', render: (r) => pct(r.percentage) },
            { key: 'weight', label: 'Weight', render: (r) => `${r.weight}%` },
            { key: 'contribution', label: 'Weighted contribution', render: (r) => r.weighted_contribution ?? 'N/A' },
            { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status} /> },
            { key: 'remarks', label: 'Remarks', render: (r) => r.remarks || '—' },
          ]}
          rows={Object.values(categories).flatMap((category) => category.indicators || [])}
        />
      </section>
    </div>
  )
}

function IndicatorsSection({ year }) {
  const queryClient = useQueryClient()
  const query = useAccomplishmentIndicators({ year })
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const mutation = useMutation({
    mutationFn: ({ id, payload }) =>
      id ? accomplishmentService.updateIndicator(id, payload) : accomplishmentService.createIndicator(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accomplishment'] })
      setOpen(false); setNotice('Indicator saved.')
    },
    onError: (err) => setError(extractError(err)),
  })

  const openForm = (item) => {
    setEditing(item)
    setForm(item ? { ...item, category_code: item.category_code } : {
      category_code: 'ACTIVITY', name: '', description: '', reporting_year: year,
      unit: UNITS[0], annual_target: '', indicator_weight: 0,
      responsible_person: '', status: 'ACTIVE', remarks: '',
    })
    setError('')
    setOpen(true)
  }

  const save = () => {
    const payload = {
      ...form,
      reporting_year: Number(form.reporting_year),
      annual_target: form.annual_target === '' ? null : Number(form.annual_target),
      indicator_weight: Number(form.indicator_weight),
    }
    mutation.mutate({ id: editing?.id, payload })
  }

  return (
    <div>
      {notice && <div className="mb-3 rounded bg-green-50 px-3 py-2 text-sm text-green-800">{notice}</div>}
      <div className="mb-4 flex justify-end">
        <button className="btn-primary" onClick={() => openForm(null)}>+ Add indicator</button>
      </div>
      <div className="card overflow-hidden">
        {query.isLoading ? <LoadingSpinner /> : query.isError ? (
          <ErrorState message={extractError(query.error)} onRetry={query.refetch} />
        ) : (
          <DataTable
            emptyMessage="No indicators yet. Add one to begin."
            columns={[
              { key: 'name', label: 'Indicator', render: (r) => r.name },
              { key: 'category', label: 'Category', render: (r) => r.category_code },
              { key: 'unit', label: 'Unit', render: (r) => r.unit },
              { key: 'annual_target', label: 'Annual target', render: (r) => r.annual_target ?? 'N/A' },
              { key: 'weight', label: 'Weight', render: (r) => `${r.indicator_weight}%` },
              { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status} /> },
              { key: 'actions', label: 'Actions', render: (r) => (
                <div className="flex flex-wrap gap-2">
                  <button className="text-xs font-medium text-brand-600 hover:underline" onClick={() => openForm(r)}>Edit</button>
                  <button className="text-xs font-medium text-red-600 hover:underline"
                    onClick={() => accomplishmentService.deleteIndicator(r.id)
                      .then(() => {
                        queryClient.invalidateQueries({ queryKey: ['accomplishment'] })
                        setNotice('Indicator removed.')
                      })
                      .catch((error) => setError(extractError(error)))}>
                    Delete
                  </button>
                </div>
              ) },
            ]}
            rows={query.data || []}
          />
        )}
      </div>
      {open && form && (
        <Modal title={editing ? 'Edit indicator' : 'Add indicator'} wide onClose={() => setOpen(false)}
          footer={<>
            <button className="btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn-primary" disabled={mutation.isPending} onClick={save}>Save</button>
          </>}>
          <div className="grid gap-4 sm:grid-cols-2">
            <div><label className="label">Category</label>
              <select className="input" value={form.category_code} onChange={(e) => setForm({ ...form, category_code: e.target.value })}>
                <option value="ACTIVITY">ACTIVITY</option><option value="DELIVERABLE">DELIVERABLE</option>
              </select></div>
            <div><label className="label">Name</label>
              <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div><label className="label">Unit</label>
              <select className="input" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })}>
                {UNITS.map((unit) => <option key={unit}>{unit}</option>)}
              </select></div>
            <div><label className="label">Annual target</label>
              <input type="number" min="0" className="input" value={form.annual_target ?? ''} onChange={(e) => setForm({ ...form, annual_target: e.target.value })} /></div>
            <div><label className="label">Indicator weight (%)</label>
              <input type="number" min="0" max="100" className="input" value={form.indicator_weight} onChange={(e) => setForm({ ...form, indicator_weight: e.target.value })} /></div>
            <div><label className="label">Responsible person / office</label>
              <input className="input" value={form.responsible_person || ''} onChange={(e) => setForm({ ...form, responsible_person: e.target.value })} /></div>
            <div><label className="label">Status</label>
              <select className="input" value={form.status || 'ACTIVE'} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                <option>ACTIVE</option><option>INACTIVE</option><option>CANCELLED</option>
              </select></div>
            <div><label className="label">Target completion date</label>
              <input type="date" className="input" value={form.target_completion_date || ''} onChange={(e) => setForm({ ...form, target_completion_date: e.target.value })} /></div>
          </div>
          <div className="mt-4"><label className="label">Description</label>
            <textarea className="input" rows="2" value={form.description || ''} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
          <p className="mt-3 text-xs text-slate-500">Annual targets are never divided across quarters automatically.</p>
        </Modal>
      )}
    </div>
  )
}

function TargetsSection({ year }) {
  const queryClient = useQueryClient()
  const indicatorsQuery = useAccomplishmentIndicators({ year })
  const query = useAccomplishmentTargets({ year })
  const [form, setForm] = useState({ indicator_id: '', quarter: 1, planned_target: '', is_approved: false })
  const [editing, setEditing] = useState(null)
  const [editForm, setEditForm] = useState({ planned_target: '', is_approved: false })
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['accomplishment', 'targets'] })
    queryClient.invalidateQueries({ queryKey: ['accomplishment', 'summary'] })
  }

  const mutation = useMutation({
    mutationFn: (payload) => accomplishmentService.createTarget(payload),
    onSuccess: () => { invalidate(); setNotice('Target saved.') },
    onError: (err) => setError(extractError(err)),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }) => accomplishmentService.updateTarget(id, payload),
    onSuccess: () => { invalidate(); setEditing(null); setNotice('Target updated.') },
    onError: (err) => setError(extractError(err)),
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => accomplishmentService.deleteTarget(id),
    onSuccess: () => { invalidate(); setNotice('Target removed.') },
    onError: (err) => setError(extractError(err)),
  })

  const targetMap = new Map((query.data || []).map((item) => [`${item.indicator_id}-${item.quarter}`, item]))

  return (
    <div>
      {notice && <div className="mb-3 rounded bg-green-50 px-3 py-2 text-sm text-green-800">{notice}</div>}
      <div className="card mb-4 p-4">
        <h2 className="mb-3 text-sm font-semibold">Set an independent quarterly target</h2>
        <div className="grid gap-3 sm:grid-cols-4">
          <select className="input" value={form.indicator_id} onChange={(e) => setForm({ ...form, indicator_id: e.target.value })}>
            <option value="">Select indicator…</option>
            {(indicatorsQuery.data || []).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
          <select className="input" value={form.quarter} onChange={(e) => setForm({ ...form, quarter: Number(e.target.value) })}>
            {[1, 2, 3, 4].map((q) => <option key={q} value={q}>Q{q}</option>)}
          </select>
          <input type="number" min="0" className="input" placeholder="Planned target"
            value={form.planned_target} onChange={(e) => setForm({ ...form, planned_target: e.target.value })} />
          <button className="btn-primary" disabled={!form.indicator_id || form.planned_target === '' || mutation.isPending}
            onClick={() => mutation.mutate({
              indicator_id: Number(form.indicator_id), reporting_year: year,
              quarter: form.quarter, planned_target: Number(form.planned_target),
              is_approved: form.is_approved,
            })}>Save target</button>
        </div>
        <label className="mt-3 flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={form.is_approved} onChange={(e) => setForm({ ...form, is_approved: e.target.checked })} />
          Approved target (only approved targets are used in calculations)
        </label>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </div>

      <div className="card overflow-hidden">
        <DataTable emptyMessage="No targets configured." columns={[
          { key: 'indicator', label: 'Indicator', render: (r) => (indicatorsQuery.data || []).find((i) => i.id === r.indicator_id)?.name || r.indicator_id },
          { key: 'quarter', label: 'Quarter', render: (r) => `Q${r.quarter}` },
          { key: 'planned', label: 'Planned', render: (r) => r.planned_target },
          { key: 'approved', label: 'Approved', render: (r) => r.is_approved ? 'Yes' : 'No' },
          { key: 'actions', label: 'Actions', render: (r) => (
            <div className="flex flex-wrap gap-2">
              <button className="text-xs font-medium text-brand-600 hover:underline"
                onClick={() => {
                  setEditing(r)
                  setEditForm({ planned_target: r.planned_target, is_approved: r.is_approved })
                  setError('')
                }}>Edit</button>
              <button className="text-xs font-medium text-brand-600 hover:underline"
                onClick={() => updateMutation.mutate({
                  id: r.id, payload: { is_approved: !r.is_approved },
                })}>
                {r.is_approved ? 'Unapprove' : 'Approve'}
              </button>
              <button className="text-xs font-medium text-red-600 hover:underline"
                onClick={() => deleteMutation.mutate(r.id)}>Delete</button>
            </div>
          ) },
        ]} rows={query.data || []} />
      </div>

      {editing && (
        <Modal
          title="Edit quarterly target"
          description={`${(indicatorsQuery.data || []).find((i) => i.id === editing.indicator_id)?.name || 'Indicator'} — Q${editing.quarter}`}
          onClose={() => setEditing(null)}
          footer={<>
            <button type="button" className="btn-secondary" onClick={() => setEditing(null)}>Cancel</button>
            <button type="button" className="btn-primary" disabled={updateMutation.isPending}
              onClick={() => updateMutation.mutate({
                id: editing.id,
                payload: {
                  planned_target: Number(editForm.planned_target),
                  is_approved: editForm.is_approved,
                },
              })}>Save changes</button>
          </>}
        >
          <div className="space-y-4">
            <div>
              <label className="label">Planned target</label>
              <input type="number" min="0" className="input"
                value={editForm.planned_target}
                onChange={(e) => setEditForm({ ...editForm, planned_target: e.target.value })} />
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={editForm.is_approved}
                onChange={(e) => setEditForm({ ...editForm, is_approved: e.target.checked })} />
              Approved target
            </label>
            {error && <p className="text-sm text-red-600">{error}</p>}
          </div>
        </Modal>
      )}
    </div>
  )
}

function ActualsSection({ year }) {
  const queryClient = useQueryClient()
  const indicatorsQuery = useAccomplishmentIndicators({ year })
  const query = useAccomplishmentActuals({ year })
  const [form, setForm] = useState({
    indicator_id: '', quarter: 1, actual_quantity: '', entry_reference: '',
    evidence_reference: '', completion_date: '',
  })
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: (payload) => accomplishmentService.createActual(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accomplishment', 'actuals'] })
      queryClient.invalidateQueries({ queryKey: ['accomplishment', 'summary'] })
      setNotice('Accomplishment recorded.')
      setForm({ ...form, actual_quantity: '', entry_reference: '', evidence_reference: '' })
    },
    onError: (err) => setError(extractError(err)),
  })

  return (
    <div>
      {notice && <div className="mb-3 rounded bg-green-50 px-3 py-2 text-sm text-green-800">{notice}</div>}
      <div className="card mb-4 p-4">
        <h2 className="mb-1 text-sm font-semibold">Record accomplishment</h2>
        <p className="mb-3 text-xs text-slate-500">Each entry needs a unique reference. This allows incremental entries without double counting.</p>
        <div className="grid gap-3 sm:grid-cols-3">
          <select className="input" value={form.indicator_id} onChange={(e) => setForm({ ...form, indicator_id: e.target.value })}>
            <option value="">Select indicator…</option>
            {(indicatorsQuery.data || []).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
          <select className="input" value={form.quarter} onChange={(e) => setForm({ ...form, quarter: Number(e.target.value) })}>
            {[1, 2, 3, 4].map((q) => <option key={q} value={q}>Q{q}</option>)}
          </select>
          <input type="number" min="0" className="input" placeholder="Actual quantity"
            value={form.actual_quantity} onChange={(e) => setForm({ ...form, actual_quantity: e.target.value })} />
          <input className="input" placeholder="Unique entry reference"
            value={form.entry_reference} onChange={(e) => setForm({ ...form, entry_reference: e.target.value })} />
          <input className="input" placeholder="Evidence reference"
            value={form.evidence_reference} onChange={(e) => setForm({ ...form, evidence_reference: e.target.value })} />
          <input type="date" className="input" value={form.completion_date} onChange={(e) => setForm({ ...form, completion_date: e.target.value })} />
        </div>
        <div className="mt-3 flex justify-end">
          <button className="btn-primary" disabled={!form.indicator_id || !form.entry_reference || form.actual_quantity === '' || mutation.isPending}
            onClick={() => mutation.mutate({
              indicator_id: Number(form.indicator_id), reporting_year: year, quarter: form.quarter,
              actual_quantity: Number(form.actual_quantity), entry_reference: form.entry_reference,
              evidence_reference: form.evidence_reference || null,
              completion_date: form.completion_date || null,
            })}>Record</button>
        </div>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </div>

      <div className="card overflow-hidden">
        <DataTable emptyMessage="No accomplishments recorded." columns={[
          { key: 'indicator', label: 'Indicator', render: (r) => (indicatorsQuery.data || []).find((i) => i.id === r.indicator_id)?.name || r.indicator_id },
          { key: 'quarter', label: 'Quarter', render: (r) => `Q${r.quarter}` },
          { key: 'quantity', label: 'Quantity', render: (r) => r.actual_quantity },
          { key: 'reference', label: 'Entry reference', render: (r) => r.entry_reference },
          { key: 'evidence', label: 'Evidence', render: (r) => r.evidence_reference || '—' },
          { key: 'status', label: 'Status', render: (r) => r.is_cancelled ? 'CANCELLED' : 'ACTIVE' },
          { key: 'actions', label: 'Actions', render: (r) => (
            <div className="flex flex-wrap gap-2">
              <button className="text-xs font-medium text-brand-600 hover:underline"
                onClick={() => accomplishmentService.updateActual(r.id, { is_cancelled: !r.is_cancelled })
                  .then(() => { queryClient.invalidateQueries({ queryKey: ['accomplishment', 'actuals'] }); queryClient.invalidateQueries({ queryKey: ['accomplishment', 'summary'] }) })}>
                {r.is_cancelled ? 'Restore' : 'Cancel entry'}
              </button>
              <button className="text-xs font-medium text-red-600 hover:underline"
                onClick={() => accomplishmentService.deleteActual(r.id)
                  .then(() => {
                    queryClient.invalidateQueries({ queryKey: ['accomplishment', 'actuals'] })
                    queryClient.invalidateQueries({ queryKey: ['accomplishment', 'summary'] })
                    setNotice('Accomplishment entry removed.')
                  })
                  .catch((error) => setError(extractError(error)))}>
                Delete
              </button>
            </div>
          ) },
        ]} rows={query.data || []} />
      </div>
    </div>
  )
}

function WeightsSection({ year }) {
  const queryClient = useQueryClient()
  const query = useAccomplishmentWeights(year)
  const [categoryDraft, setCategoryDraft] = useState(null)
  const [indicatorDraft, setIndicatorDraft] = useState(null)
  const [message, setMessage] = useState('')

  const data = query.data
  const categoryTotal = categoryDraft
    ? Object.values(categoryDraft).reduce((sum, value) => sum + Number(value || 0), 0)
    : (data?.categories || []).reduce((sum, item) => sum + Number(item.weight || 0), 0)
  const indicatorTotal = indicatorDraft
    ? Object.values(indicatorDraft).reduce((sum, value) => sum + Number(value || 0), 0)
    : (data?.indicators || []).reduce((sum, item) => sum + Number(item.weight || 0), 0)
  const valid = categoryTotal === 100 && indicatorTotal === 100

  if (query.isLoading) return <LoadingSpinner />
  if (query.isError) return <ErrorState message={extractError(query.error)} onRetry={query.refetch} />

  const categories = data?.categories || []
  const indicators = data?.indicators || []

  const save = async () => {
    try {
      await accomplishmentService.saveWeights({
        reporting_year: year,
        category_weights: Object.fromEntries(
          Object.entries(categoryDraft || {}).map(([key, value]) => [key, Number(value)])
        ),
        indicator_weights: indicators.map((item) => ({
          indicator_id: item.id,
          weight: Number((indicatorDraft || {})[item.id] ?? item.weight),
        })),
        reason: 'Updated in weight configuration screen',
      })
      queryClient.invalidateQueries({ queryKey: ['accomplishment'] })
      setMessage('Weights saved. Previous values were recorded in history.')
      setCategoryDraft(null); setIndicatorDraft(null)
    } catch (err) {
      setMessage(extractError(err))
    }
  }

  return (
    <div className="space-y-5">
      <div className="card p-5">
        <h2 className="mb-1 text-sm font-semibold">Level 1 — Category weights</h2>
        <p className="mb-4 text-xs text-slate-500">Defaults of 50% / 50% are configurable examples, not official standards.</p>
        {categories.map((category) => (
          <div key={category.code} className="mb-3 flex items-center gap-3">
            <span className="w-40 text-sm">{category.name} ({category.code})</span>
            <input type="number" min="0" max="100" className="input w-24"
              value={categoryDraft?.[category.code] ?? category.weight}
              onChange={(e) => setCategoryDraft({ ...categoryDraft, [category.code]: e.target.value })} />
            <span className="text-sm text-slate-500">%</span>
          </div>
        ))}
        <p className={`text-sm font-medium ${categoryTotal === 100 ? 'text-green-700' : 'text-red-700'}`}>
          Total: {categoryTotal}% {categoryTotal !== 100 && '(must equal 100%)'}
        </p>
      </div>

      <div className="card p-5">
        <h2 className="mb-4 text-sm font-semibold">Level 2 — Indicator weights within each category</h2>
        {indicators.length === 0 && <p className="text-sm text-slate-500">No indicators configured.</p>}
        {indicators.map((item) => (
          <div key={item.id} className="mb-3 flex items-center gap-3">
            <span className="w-56 truncate text-sm">{item.name} <span className="text-xs text-slate-500">({item.category})</span></span>
            <input type="number" min="0" max="100" className="input w-24"
              value={indicatorDraft?.[item.id] ?? item.weight}
              onChange={(e) => setIndicatorDraft({ ...indicatorDraft, [item.id]: e.target.value })} />
            <span className="text-sm text-slate-500">%</span>
          </div>
        ))}
        <p className={`text-sm font-medium ${indicatorTotal === 100 ? 'text-green-700' : 'text-red-700'}`}>
          Total: {indicatorTotal}% {indicatorTotal !== 100 && '(must equal 100%)'}
        </p>
        <p className="mt-1 text-xs text-slate-500">Weights are validated per category-year on the backend as well.</p>
      </div>

      <div className="flex justify-end">
        <button className="btn-primary" disabled={!valid} onClick={save}>Save weights</button>
      </div>
      {message && <p className={`text-sm ${message.startsWith('Weights saved') ? 'text-green-700' : 'text-red-600'}`}>{message}</p>}

      <div className="card overflow-hidden">
        <div className="border-b border-slate-200 px-4 py-3 text-sm font-semibold">Weight change history</div>
        <DataTable emptyMessage="No weight changes recorded." columns={[
          { key: 'scope', label: 'Scope', render: (r) => r.scope },
          { key: 'year', label: 'Year', render: (r) => r.year },
          { key: 'old', label: 'Old', render: (r) => r.old_value ?? '—' },
          { key: 'new', label: 'New', render: (r) => r.new_value },
          { key: 'reason', label: 'Reason', render: (r) => r.reason || '—' },
          { key: 'at', label: 'Changed at', render: (r) => new Date(r.changed_at).toLocaleString() },
        ]} rows={data?.history || []} />
      </div>
    </div>
  )
}

function AnnualSection({ year }) {
  const summary = useAccomplishmentSummary(year)
  const completeness = useDataCompleteness({ date_from: `${year}-01-01`, date_to: `${year}-12-31` })
  const data = summary.data?.annual

  return (
    <div className="space-y-5">
      <section className="grid gap-3 sm:grid-cols-3">
        <SummaryCard label="Overall annual accomplishment" value={pct(data?.overall)} />
        <SummaryCard label="Activities score" value={pct(data?.categories?.ACTIVITY?.score)} />
        <SummaryCard label="Deliverables score" value={pct(data?.categories?.DELIVERABLE?.score)} />
      </section>

      <div className="card overflow-hidden">
        <div className="border-b border-slate-200 px-4 py-3 text-sm font-semibold">Annual indicator totals</div>
        <DataTable emptyMessage="No annual data." columns={[
          { key: 'name', label: 'Indicator', render: (r) => r.name },
          { key: 'category', label: 'Category', render: (r) => r.category },
          { key: 'planned', label: 'Total planned', render: (r) => r.planned_target ?? 'N/A' },
          { key: 'actual', label: 'Total actual', render: (r) => r.actual_accomplishment ?? '—' },
          { key: 'percentage', label: 'Accomplishment', render: (r) => pct(r.percentage) },
          { key: 'contribution', label: 'Weighted contribution', render: (r) => r.weighted_contribution ?? 'N/A' },
        ]} rows={Object.values(data?.categories || {}).flatMap((c) => c.indicators || [])} />
      </div>

      <div className="card p-5">
        <h2 className="mb-3 text-sm font-semibold">Environmental Data Completeness (separate technical KPI)</h2>
        {completeness.isLoading ? <LoadingSpinner /> : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <SummaryCard label="Expected readings" value={completeness.data?.expected_readings ?? '—'} />
            <SummaryCard label="Valid readings" value={completeness.data?.valid_readings ?? '—'} tone="green" />
            <SummaryCard label="Missing readings" value={completeness.data?.missing_readings ?? '—'} tone="amber" />
            <SummaryCard label="Completeness" value={pct(completeness.data?.completeness_percent)} />
          </div>
        )}
        <p className="mt-3 text-xs text-slate-500">
          Invalid and duplicate readings are excluded. Missing readings are not counted as zero.
        </p>
      </div>
    </div>
  )
}

function ReportsSection({ year }) {
  const queryClient = useQueryClient()
  const query = useAccomplishmentReports()
  const [form, setForm] = useState({ report_type: 'quarterly', quarter: 1, file_format: 'pdf' })
  const [notice, setNotice] = useState('')

  const generate = useMutation({
    mutationFn: (payload) => accomplishmentService.generateReport(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accomplishment', 'reports'] })
      setNotice('Draft report created. Generate a file, then finalize it.')
    },
    onError: (err) => setNotice(extractError(err)),
  })

  const action = useMutation({
    mutationFn: ({ id, kind }) =>
      kind === 'finalize' ? accomplishmentService.finalizeReport(id) : accomplishmentService.reviseReport(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accomplishment', 'reports'] })
      setNotice('Report updated.')
    },
    onError: (err) => setNotice(extractError(err)),
  })

  return (
    <div>
      {notice && <div className="mb-3 rounded bg-green-50 px-3 py-2 text-sm text-green-800">{notice}</div>}
      <div className="card mb-4 p-4">
        <h2 className="mb-3 text-sm font-semibold">Generate an accomplishment report</h2>
        <div className="grid gap-3 sm:grid-cols-4">
          <select className="input" value={form.report_type} onChange={(e) => setForm({ ...form, report_type: e.target.value })}>
            <option value="quarterly">Quarterly</option><option value="q1">Q1</option>
            <option value="q2">Q2</option><option value="q3">Q3</option><option value="q4">Q4</option>
            <option value="annual">Annual</option><option value="activities">Activities</option>
            <option value="deliverables">Deliverables</option><option value="data_completeness">Data completeness</option>
          </select>
          {['quarterly', 'q1', 'q2', 'q3', 'q4'].includes(form.report_type) && (
            <select className="input" value={form.quarter} onChange={(e) => setForm({ ...form, quarter: Number(e.target.value) })}>
              {[1, 2, 3, 4].map((q) => <option key={q} value={q}>Q{q}</option>)}
            </select>
          )}
          <select className="input" value={form.file_format} onChange={(e) => setForm({ ...form, file_format: e.target.value })}>
            <option value="pdf">PDF</option><option value="xlsx">Excel</option>
          </select>
          <button className="btn-primary" disabled={generate.isPending} onClick={() => generate.mutate({
            reporting_year: year,
            quarter: ['quarterly', 'q1', 'q2', 'q3', 'q4'].includes(form.report_type) ? form.quarter : null,
            report_type: form.report_type,
            file_format: form.file_format,
          })}>Generate draft</button>
        </div>
      </div>

      <div className="card overflow-hidden">
        <DataTable emptyMessage="No reports generated." columns={[
          { key: 'number', label: 'Report', render: (r) => r.report_number },
          { key: 'type', label: 'Type', render: (r) => r.report_type },
          { key: 'period', label: 'Period', render: (r) => `Q${r.quarter ?? '—'} ${r.reporting_year}` },
          { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status} /> },
          { key: 'version', label: 'Version', render: (r) => r.version },
          { key: 'actions', label: 'Actions', render: (r) => (
            <div className="flex flex-wrap gap-2">
              <button className="text-xs font-medium text-brand-600 hover:underline"
                onClick={() => accomplishmentService.buildFile(r.id, r.file_format || 'pdf')
                  .then(() => queryClient.invalidateQueries({ queryKey: ['accomplishment', 'reports'] }))}>
                Build file
              </button>
              {r.file_name && (
                <button type="button" className="text-xs font-medium text-brand-600 hover:underline"
                  onClick={() => accomplishmentService.download(r.id, r.file_name).catch((error) => setNotice(extractError(error)))}>
                  Download
                </button>
              )}
              {r.status === 'DRAFT' && <button className="text-xs font-medium text-green-700 hover:underline"
                onClick={() => action.mutate({ id: r.id, kind: 'finalize' })}>Finalize</button>}
              {r.status === 'FINAL' && <button className="text-xs font-medium text-brand-600 hover:underline"
                onClick={() => action.mutate({ id: r.id, kind: 'revise' })}>Revise</button>}
            </div>
          ) },
        ]} rows={query.data || []} />
      </div>
    </div>
  )
}

export default function AccomplishmentPage({ section = 'dashboard' }) {
  const [year, setYear] = useState(currentYear())
  const [quarter, setQuarter] = useState(null)
  const [activeSection, setActiveSection] = useState(section)

  return (
    <div>
      <PageHeader
        title="Quarterly Accomplishment"
        description="Weighted activity and deliverable accomplishment reporting, with separate environmental data completeness."
        actions={
          <div className="flex gap-2">
            <select className="input w-28" value={year} onChange={(e) => setYear(Number(e.target.value))}>
              {Array.from({ length: 7 }, (_, index) => currentYear() - 5 + index).map((item) => <option key={item}>{item}</option>)}
            </select>
            <select className="input w-32" value={quarter ?? ''} onChange={(e) => setQuarter(e.target.value ? Number(e.target.value) : null)}>
              <option value="">Annual / all</option>
              {[1, 2, 3, 4].map((q) => <option key={q} value={q}>Q{q}</option>)}
            </select>
          </div>
        }
      />

      <SectionTabs section={activeSection} setSection={setActiveSection} />

      {activeSection === 'dashboard' && <DashboardSection year={year} quarter={quarter} />}
      {activeSection === 'indicators' && <IndicatorsSection year={year} />}
      {activeSection === 'targets' && <TargetsSection year={year} />}
      {activeSection === 'actuals' && <ActualsSection year={year} />}
      {activeSection === 'weights' && <WeightsSection year={year} />}
      {activeSection === 'annual' && <AnnualSection year={year} />}
      {activeSection === 'reports' && <ReportsSection year={year} />}
    </div>
  )
}
