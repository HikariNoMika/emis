import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import DataTable from '../components/ui/DataTable'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import Modal from '../components/ui/Modal'
import PageHeader from '../components/ui/PageHeader'
import Pagination from '../components/ui/Pagination'
import StatusBadge from '../components/ui/StatusBadge'
import { useUsers } from '../hooks/useUsers'
import { extractError } from '../services/api'
import userService from '../services/userService'

const emptyForm = () => ({
  username: '', email: '', full_name: '', password: '', confirm_password: '',
  role: 'admin', is_active: true,
})

export default function UsersPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [role, setRole] = useState('')
  const [page, setPage] = useState(1)
  const [form, setForm] = useState(null)
  const [editing, setEditing] = useState(null)
  const [resetTarget, setResetTarget] = useState(null)
  const [resetForm, setResetForm] = useState({ new_password: '', confirm_password: '', must_change_password: true })
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  const query = useUsers({
    page, per_page: 15,
    ...(search ? { search } : {}),
    ...(role ? { role } : {}),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['users'] })

  const saveMutation = useMutation({
    mutationFn: ({ id, payload }) => id ? userService.update(id, payload) : userService.create(payload),
    onSuccess: () => { invalidate(); setForm(null); setNotice('User saved.') },
    onError: (err) => setError(extractError(err)),
  })

  const activeMutation = useMutation({
    mutationFn: ({ id, active }) => userService.setActive(id, active),
    onSuccess: () => { invalidate(); setNotice('User status updated.') },
    onError: (err) => setNotice(extractError(err)),
  })

  const resetMutation = useMutation({
    mutationFn: ({ id, payload }) => userService.resetPassword(id, payload),
    onSuccess: () => { setResetTarget(null); setNotice('Password reset.') },
    onError: (err) => setError(extractError(err)),
  })

  const openCreate = () => { setEditing(null); setForm(emptyForm()); setError('') }
  const openEdit = (user) => {
    setEditing(user)
    setForm({
      username: user.username, email: user.email, full_name: user.full_name,
      role: user.role, is_active: user.is_active,
      password: '', confirm_password: '',
    })
    setError('')
  }

  const save = () => {
    const payload = editing
      ? { email: form.email, full_name: form.full_name, role: form.role, is_active: form.is_active }
      : form
    saveMutation.mutate({ id: editing?.id, payload })
  }

  const columns = [
    { key: 'username', label: 'Username', render: (r) => <span className="font-medium">{r.username}</span> },
    { key: 'name', label: 'Name', render: (r) => r.full_name },
    { key: 'email', label: 'Email', render: (r) => r.email },
    { key: 'role', label: 'Role', render: (r) => <span className="capitalize">{r.role}</span> },
    { key: 'active', label: 'Status', render: (r) => <StatusBadge status={r.is_active ? 'ONLINE' : 'OFFLINE'} /> },
    { key: 'last_login', label: 'Last login', render: (r) => r.last_login_at ? new Date(r.last_login_at).toLocaleString() : '—' },
    { key: 'actions', label: 'Actions', render: (r) => (
      <div className="flex flex-wrap gap-2">
        <button className="text-xs font-medium text-brand-600 hover:underline" onClick={() => openEdit(r)}>Edit</button>
        <button className="text-xs font-medium text-brand-600 hover:underline"
          onClick={() => { setResetTarget(r); setResetForm({ new_password: '', confirm_password: '', must_change_password: true }); setError('') }}>
          Reset password
        </button>
        <button className="text-xs font-medium text-slate-600 hover:underline"
          onClick={() => activeMutation.mutate({ id: r.id, active: !r.is_active })}>
          {r.is_active ? 'Deactivate' : 'Activate'}
        </button>
      </div>
    ) },
  ]

  return (
    <div>
      <PageHeader title="User Management"
        description="Create administrator accounts, manage roles and activate or deactivate access."
        actions={<button className="btn-primary" onClick={openCreate}>+ Add user</button>} />

      {notice && <div className="mb-3 rounded bg-green-50 px-3 py-2 text-sm text-green-800">{notice}</div>}

      <div className="card mb-4 flex flex-col gap-3 p-4 sm:flex-row">
        <input className="input flex-1" placeholder="Search username, name or email…" value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }} />
        <select className="input sm:w-44" value={role} onChange={(e) => { setRole(e.target.value); setPage(1) }}>
          <option value="">All roles</option>
          <option value="admin">Admin</option>
          <option value="viewer">Viewer</option>
        </select>
      </div>

      <div className="card overflow-hidden">
        {query.isLoading ? <LoadingSpinner /> : query.isError ? (
          <ErrorState message={extractError(query.error)} onRetry={query.refetch} />
        ) : (
          <>
            <DataTable rows={query.data?.data || []} columns={columns} emptyMessage="No users found." />
            <Pagination meta={query.data?.meta} onPageChange={setPage} />
          </>
        )}
      </div>

      {form && (
        <Modal title={editing ? 'Edit user' : 'Create user'} wide onClose={() => setForm(null)}
          footer={<>
            <button className="btn-secondary" onClick={() => setForm(null)}>Cancel</button>
            <button className="btn-primary" disabled={saveMutation.isPending} onClick={save}>Save</button>
          </>}>
          <div className="grid gap-4 sm:grid-cols-2">
            <div><label className="label">Username</label>
              <input className="input" value={form.username} disabled={Boolean(editing)}
                onChange={(e) => setForm({ ...form, username: e.target.value })} /></div>
            <div><label className="label">Full name</label>
              <input className="input" value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></div>
            <div><label className="label">Email</label>
              <input className="input" type="email" value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
            <div><label className="label">Role</label>
              <select className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                <option value="admin">Admin</option><option value="viewer">Viewer</option>
              </select></div>
            {!editing && <>
              <div><label className="label">Password</label>
                <input className="input" type="password" value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })} /></div>
              <div><label className="label">Confirm password</label>
                <input className="input" type="password" value={form.confirm_password}
                  onChange={(e) => setForm({ ...form, confirm_password: e.target.value })} /></div>
            </>}
          </div>
          {!editing && <label className="mt-3 flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
            Active (user can log in)
          </label>}
          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
          <p className="mt-3 text-xs text-slate-500">New users must change their password at first login.</p>
        </Modal>
      )}

      {resetTarget && (
        <Modal title={`Reset password — ${resetTarget.username}`} onClose={() => setResetTarget(null)}
          footer={<>
            <button className="btn-secondary" onClick={() => setResetTarget(null)}>Cancel</button>
            <button className="btn-primary" disabled={resetMutation.isPending}
              onClick={() => resetMutation.mutate({ id: resetTarget.id, payload: resetForm })}>Reset password</button>
          </>}>
          <div className="space-y-3">
            <div><label className="label">New password</label>
              <input className="input" type="password" value={resetForm.new_password}
                onChange={(e) => setResetForm({ ...resetForm, new_password: e.target.value })} /></div>
            <div><label className="label">Confirm password</label>
              <input className="input" type="password" value={resetForm.confirm_password}
                onChange={(e) => setResetForm({ ...resetForm, confirm_password: e.target.value })} /></div>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={resetForm.must_change_password}
                onChange={(e) => setResetForm({ ...resetForm, must_change_password: e.target.checked })} />
              Require password change at next login
            </label>
            {error && <p className="text-sm text-red-600">{error}</p>}
          </div>
        </Modal>
      )}
    </div>
  )
}
