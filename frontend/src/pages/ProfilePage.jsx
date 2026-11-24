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
  const [mfaSetup, setMfaSetup] = useState(null)
  const [mfaCode, setMfaCode] = useState('')
  const [recoveryCodes, setRecoveryCodes] = useState([])
  const [disableCode, setDisableCode] = useState('')

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
      const result = await authService.changePassword(
        passwords.current_password,
        passwords.new_password,
        passwords.confirm_password,
      )
      setPasswords({ current_password: '', new_password: '', confirm_password: '' })
      if (result?.mfa_enrolment) {
        setMfaSetup(result.mfa_enrolment)
        setRecoveryCodes(result.mfa_enrolment.recovery_codes || [])
        await refreshProfile()
        setNotice('Password changed. Set up your authenticator now.')
      } else {
        setNotice('Password changed.')
      }
    } catch (err) {
      setError(extractError(err))
    }
  }

  const startMfa = async () => {
    setError('')
    try {
      setMfaSetup(await authService.mfaSetup())
      setMfaCode('')
    } catch (err) {
      setError(extractError(err))
    }
  }

  const enableMfa = async (event) => {
    event.preventDefault()
    setError('')
    try {
      const result = await authService.mfaEnable(mfaCode)
      setRecoveryCodes(result.recovery_codes || [])
      setMfaSetup(null)
      setMfaCode('')
      await refreshProfile()
      setNotice('MFA enabled. Save your recovery codes now.')
    } catch (err) {
      setError(extractError(err))
    }
  }

  const disableMfa = async (event) => {
    event.preventDefault()
    setError('')
    try {
      await authService.mfaDisable(passwords.current_password, disableCode)
      setDisableCode('')
      setRecoveryCodes([])
      await refreshProfile()
      setNotice('MFA disabled.')
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

      <section className="card mt-6 space-y-4 p-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Two-factor authentication</h2>
            <p className="mt-1 text-xs text-slate-500">
              {user?.mfa_enabled
                ? 'MFA is active on this account.'
                : 'Add an authenticator app for an extra layer of security.'}
            </p>
          </div>
          <span className={`badge ${user?.mfa_enabled ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-600'}`}>
            {user?.mfa_enabled ? 'Enabled' : 'Disabled'}
          </span>
        </div>

        {!user?.mfa_enabled && !mfaSetup && (
          <button type="button" className="btn-secondary" onClick={startMfa}>
            Set up authenticator
          </button>
        )}

        {mfaSetup && (
          <form onSubmit={enableMfa} className="space-y-3 rounded border border-slate-200 p-3">
            {mfaSetup.qr_data_uri && (
              <div className="flex justify-center rounded border border-slate-200 bg-white p-3">
                <img src={mfaSetup.qr_data_uri} alt="Authenticator QR code" className="h-40 w-40" />
              </div>
            )}
            <p className="text-xs text-slate-600">
              Scan the QR code with your authenticator app, or enter the secret manually.
              {mfaSetup.email_sent && ' The secret was also emailed to you.'}
              Then enter the 6-digit code:
            </p>
            <code className="block break-all rounded bg-slate-50 p-2 text-xs">{mfaSetup.secret}</code>
            <input
              className="input text-center tracking-widest"
              inputMode="numeric"
              maxLength={6}
              placeholder="000000"
              value={mfaCode}
              onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, ''))}
            />
            <div className="flex gap-2">
              <button className="btn-primary" type="submit" disabled={mfaCode.length !== 6}>Enable MFA</button>
              <button type="button" className="btn-secondary" onClick={() => setMfaSetup(null)}>Cancel</button>
            </div>
          </form>
        )}

        {recoveryCodes.length > 0 && (
          <div className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            <p className="font-medium">Save these recovery codes — shown once:</p>
            <div className="mt-2 grid grid-cols-2 gap-1 font-mono text-xs">
              {recoveryCodes.map((code) => <span key={code}>{code}</span>)}
            </div>
            <button type="button" className="mt-3 text-xs underline" onClick={() => setRecoveryCodes([])}>
              I have saved them
            </button>
          </div>
        )}

        {user?.mfa_enabled && (
          <form onSubmit={disableMfa} className="flex flex-wrap items-end gap-2 border-t border-slate-200 pt-4">
            <div className="flex-1">
              <label className="label">Current password</label>
              <input className="input" type="password" value={passwords.current_password}
                onChange={(e) => setPasswords({ ...passwords, current_password: e.target.value })} />
            </div>
            <div className="flex-1">
              <label className="label">Authenticator code</label>
              <input className="input" inputMode="numeric" maxLength={6} value={disableCode}
                onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, ''))} />
            </div>
            <button className="btn-secondary" type="submit" disabled={disableCode.length !== 6}>Disable MFA</button>
          </form>
        )}
      </section>
    </div>
  )
}
