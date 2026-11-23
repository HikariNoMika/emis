import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import authService from '../services/authService'
import { getAccessToken } from '../services/api'

const AuthContext = createContext(null)

/**
 * Holds the logged-in administrator for the whole application.
 * Components read it with useAuth() instead of passing props down manually.
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

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
    const profile = await authService.login(identifier, password)
    setUser(profile)
    return profile
  }, [])

  const logout = useCallback(async () => {
    await authService.logout()
    setUser(null)
  }, [])

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
      logout,
      refreshProfile,
    }),
    [user, isLoading, login, logout, refreshProfile],
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
