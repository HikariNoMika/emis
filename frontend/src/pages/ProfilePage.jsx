import { useState } from 'react'
import PageHeader from '../components/ui/PageHeader'
import { useAuth } from '../context/AuthContext'
import { extractError } from '../services/api'
import authService from '../services/authService'
import userService from '../services/userService'

export default function ProfilePage() {
  const { user, refreshProfile } = useAuth()
  const [profile, setProfile] = useState({
    full_name: user?.full_name || '',
    email: user?.email || '',
  })
  const [passwords, setPasswords] = useState({
    current_password: '', new_password: '', confirm_password: '',
  })
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  const saveProfile = async (event) => {
    event.preventDefault()
    setError('')
    try {
      await userService.updateProfile(profile)
      await refreshProfile()
      setNotice('Profile updated.')
    } catch (err) {
      setError(extractError(err))
    }
  }

  const savePassword = async (event) => {
    event.preventDefault()
    setError('')
    try {
      await authService.changePassword(
        passwords.current_password,
        passwords.new_password,
        passwords.confirm_password,
      )
      setPasswords({ current_password: '', new_password: '', confirm_password: '' })
      setNotice('Password changed.')
    } catch (err) {
      setError(extractError(err))
    }
  }

  return (
    <div className="max-w-2xl">
      <PageHeader title="My Profile" description="Edit your account details and password." />

      {notice && <div className="mb-4 rounded bg-green-50 px-3 py-2 text-sm text-green-800">{notice}</div>}
      {error && <div className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}

      <form onSubmit={saveProfile} className="card mb-6 space-y-4 p-5">
        <h2 className="text-sm font-semibold text-slate-900">Account details</h2>
        <div>
          <label className="label">Username</label>
          <input className="input bg-slate-50" value={user?.username || ''} disabled />
        </div>
        <div>
          <label className="label">Full name</label>
          <input className="input" value={profile.full_name}
            onChange={(e) => setProfile({ ...profile, full_name: e.target.value })} />
        </div>
        <div>
          <label className="label">Email</label>
          <input className="input" type="email" value={profile.email}
            onChange={(e) => setProfile({ ...profile, email: e.target.value })} />
        </div>
        <div className="flex justify-end">
          <button className="btn-primary" type="submit">Save profile</button>
        </div>
      </form>

      <form onSubmit={savePassword} className="card space-y-4 p-5">
        <h2 className="text-sm font-semibold text-slate-900">Change password</h2>
        <div>
          <label className="label">Current password</label>
          <input className="input" type="password" value={passwords.current_password}
            onChange={(e) => setPasswords({ ...passwords, current_password: e.target.value })} />
        </div>
        <div>
          <label className="label">New password</label>
          <input className="input" type="password" value={passwords.new_password}
            onChange={(e) => setPasswords({ ...passwords, new_password: e.target.value })} />
        </div>
        <div>
          <label className="label">Confirm new password</label>
          <input className="input" type="password" value={passwords.confirm_password}
            onChange={(e) => setPasswords({ ...passwords, confirm_password: e.target.value })} />
        </div>
        <div className="flex justify-end">
          <button className="btn-primary" type="submit">Change password</button>
        </div>
      </form>
    </div>
  )
}
