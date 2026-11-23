import { Navigate, useLocation } from 'react-router-dom'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import { useAuth } from '../context/AuthContext'

/** Blocks access to a page unless an administrator is logged in. */
export default function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return <LoadingSpinner label="Checking your session…" />
  }

  if (!isAuthenticated) {
    // Remember where the user wanted to go so we can send them back after login.
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return children
}
