import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import Header from './Header'
import Sidebar from './Sidebar'

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const { idleWarning, dismissIdleWarning, user } = useAuth()

  return (
    <div className="flex h-full">
      <div className="hidden md:flex">
        <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((value) => !value)} />
      </div>

      {/* Mobile navigation drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 w-64">
            <Sidebar collapsed={false} onToggle={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <Header onOpenMobileMenu={() => setMobileOpen(true)} />
        {user?.must_change_password && (
          <div className="border-b border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">
            <strong>Action required:</strong> you must change your password before using the system.
            Open <a className="underline" href="/profile">My Profile</a> to update it.
          </div>
        )}
        {idleWarning && (
          <div className="flex items-center justify-between gap-3 border-b border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900">
            <span>
              You have been inactive. You will be signed out in about 2 minutes.
            </span>
            <button
              type="button"
              className="rounded border border-amber-300 bg-white px-2 py-1 text-xs font-medium hover:bg-amber-100"
              onClick={dismissIdleWarning}
            >
              Stay signed in
            </button>
          </div>
        )}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
