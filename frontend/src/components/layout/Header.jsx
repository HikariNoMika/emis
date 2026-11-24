import { useState } from 'react'
import { Link } from 'react-router-dom'
import { LogOut, Menu, UserCircle2 } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'

export default function Header({ onOpenMobileMenu }) {
  const { user, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const [isSigningOut, setIsSigningOut] = useState(false)

  const handleSignOut = async () => {
    setIsSigningOut(true)
    try {
      await logout()
    } catch {
      // Local tokens are cleared by the service even when the API call fails.
    } finally {
      setIsSigningOut(false)
    }
  }

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 shadow-sm sm:px-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onOpenMobileMenu}
          className="rounded p-2 text-slate-600 hover:bg-slate-100 md:hidden"
          aria-label="Open navigation"
        >
          <Menu size={20} />
        </button>
        <div>
          <p className="text-sm font-semibold text-slate-900">
            PFMS Watershed
          </p>
          <p className="hidden text-xs text-slate-500 sm:block">
            Administration Portal
          </p>
        </div>
      </div>

      <div className="relative">
        <button
          type="button"
          onClick={() => setMenuOpen((open) => !open)}
          className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-slate-100"
        >
          <UserCircle2 size={22} className="text-brand-600" />
          <span className="hidden text-left sm:block">
            <span className="block font-medium text-slate-800">
              {user?.full_name || user?.username}
            </span>
            <span className="block text-xs capitalize text-slate-500">
              {user?.role}
            </span>
          </span>
        </button>

        {menuOpen && (
          <div className="absolute right-0 mt-2 w-52 rounded-md border border-slate-200 bg-white py-1 shadow-lg">
            <div className="border-b border-slate-100 px-4 py-2 text-xs text-slate-500">
              Signed in as {user?.username}
            </div>
            <Link
              to="/profile"
              onClick={() => setMenuOpen(false)}
              className="block px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
            >
              My profile
            </Link>
            <button
              type="button"
              onClick={handleSignOut}
              disabled={isSigningOut}
              className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
            >
              <LogOut size={16} /> {isSigningOut ? 'Signing out…' : 'Sign out'}
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
