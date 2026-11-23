import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { useAuth } from '../context/AuthContext'
import { extractError } from '../services/api'

// Zod validates the form before it is submitted — no invalid request reaches Flask.
const loginSchema = z.object({
  identifier: z.string().min(1, 'Username or email is required'),
  password: z.string().min(1, 'Password is required'),
})

export default function LoginPage() {
  const { login, isAuthenticated, isLoading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [serverError, setServerError] = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { identifier: '', password: '' },
  })

  if (isLoading) return null
  if (isAuthenticated) {
    return <Navigate to={location.state?.from || '/'} replace />
  }

  const onSubmit = async (values) => {
    setServerError('')
    try {
      await login(values.identifier, values.password)
      navigate(location.state?.from || '/', { replace: true })
    } catch (error) {
      setServerError(extractError(error))
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center bg-slate-100 px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-lg bg-brand-700 text-lg font-bold text-white">
            EM
          </div>
          <h1 className="text-xl font-semibold text-slate-900">
            Environmental Monitoring Information System
          </h1>
          <p className="mt-1 text-sm text-slate-600">Administrator sign in</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="card space-y-4 p-6">
          {serverError && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {serverError}
            </div>
          )}

          <div>
            <label className="label" htmlFor="identifier">
              Username or email
            </label>
            <input
              id="identifier"
              className="input"
              autoComplete="username"
              {...register('identifier')}
            />
            {errors.identifier && (
              <p className="mt-1 text-xs text-red-600">{errors.identifier.message}</p>
            )}
          </div>

          <div>
            <label className="label" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              className="input"
              autoComplete="current-password"
              {...register('password')}
            />
            {errors.password && (
              <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>
            )}
          </div>

          <button type="submit" className="btn-primary w-full" disabled={isSubmitting}>
            {isSubmitting ? 'Signing in…' : 'Sign in'}
          </button>

          <p className="text-center text-xs text-slate-500">
            Access is restricted to authorized administrators.
          </p>
        </form>
      </div>
    </div>
  )
}
