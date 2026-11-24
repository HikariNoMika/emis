import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import authService from '../services/authService'
import { getAccessToken } from '../services/api'

const AuthContext = createContext(null)

// Idle timeout: log the administrator out after 30 minutes of no interaction.
const IDLE_MS = 30 * 60 * 1000
const WARN_MS = 2 * 60 * 1000 // warn 2 minutes before logout
const ACTIVITY_EVENTS = ['click', 'keydown', 'mousemove', 'scroll', 'touchstart']

/**
 * Holds the logged-in administrator for the whole application.
 * Components read it with useAuth() instead of passing props down manually.
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [idleWarning, setIdleWarning] = useState(false)

  // On first load, restore the session if a token is stored.
  useEffect(() => {
    let active = true

    async function restoreSession() {
      if (!getAccessToken()) {
        setIsLoading(false)
        return
      }
      try {
        const profile = await authService.me()
        if (active) setUser(profile)
      } catch {
        if (active) setUser(null)
      } finally {
        if (active) setIsLoading(false)
      }
    }

    restoreSession()
    return () => {
      active = false
    }
  }, [])

  // The API client fires this event when a refresh fails.
  useEffect(() => {
    const handleUnauthorized = () => setUser(null)
    window.addEventListener('emis:unauthorized', handleUnauthorized)
    return () => window.removeEventListener('emis:unauthorized', handleUnauthorized)
  }, [])

  const login = useCallback(async (identifier, password) => {
    const result = await authService.login(identifier, password)
    if (result?.mfaRequired) return result
    setUser(result)
    return result
  }, [])

  const verifyMfa = useCallback(async (mfaToken, code) => {
    const profile = await authService.verifyMfa(mfaToken, code)
    setUser(profile)
    return profile
  }, [])

  const logout = useCallback(async () => {
    await authService.logout()
    setUser(null)
  }, [])

  // Idle timeout: reset a timer on any user activity. Show a warning shortly
  // before logout, then sign out and clear the tokens.
  useEffect(() => {
    if (!user) {
      setIdleWarning(false)
      return undefined
    }
    let idleTimer
    let warnTimer

    const schedule = () => {
      clearTimeout(idleTimer)
      clearTimeout(warnTimer)
      setIdleWarning(false)
      warnTimer = setTimeout(() => setIdleWarning(true), IDLE_MS - WARN_MS)
      idleTimer = setTimeout(() => {
        authService.logout().catch(() => {})
        setUser(null)
        setIdleWarning(false)
      }, IDLE_MS)
    }

    ACTIVITY_EVENTS.forEach((event) => window.addEventListener(event, schedule, { passive: true }))
    schedule()
    return () => {
      ACTIVITY_EVENTS.forEach((event) => window.removeEventListener(event, schedule))
      clearTimeout(idleTimer)
      clearTimeout(warnTimer)
    }
  }, [user])

  // Re-fetch the profile after the user edits their own details.
  const refreshProfile = useCallback(async () => {
    const profile = await authService.me()
    setUser(profile)
    return profile
  }, [])

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      login,
      verifyMfa,
      logout,
      refreshProfile,
      idleWarning,
      dismissIdleWarning: () => { setIdleWarning(false); window.dispatchEvent(new Event('click')) },
    }),
    [user, isLoading, login, verifyMfa, logout, refreshProfile, idleWarning],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside an AuthProvider')
  }
  return context
}

export default AuthContext
