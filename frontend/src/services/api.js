import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const TOKEN_KEY = 'emis_access_token'
const REFRESH_KEY = 'emis_refresh_token'

// ---------------------------------------------------------------------------
// Token storage helpers
// ---------------------------------------------------------------------------
// Tokens are kept in localStorage so a page refresh does not log the user out.
// This is simple and works well for an internal admin tool. For a public app,
// prefer an HttpOnly cookie so JavaScript cannot read the token at all.
export function getAccessToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setTokens(accessToken, refreshToken) {
  localStorage.setItem(TOKEN_KEY, accessToken)
  if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken)
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  // Uploads and import processing can take longer than 30s on a remote server.
  timeout: 180000,
})

// Attach the access token to every outgoing request.
api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let isRefreshing = false
let waitingRequests = []

// When a token expires, try to replace it using the refresh token.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const status = error.response?.status

    if (status === 401 && originalRequest && !originalRequest._retry) {
      // If the failure happened on the login endpoint, do not try to refresh.
      if (originalRequest.url?.includes('/auth/login')) {
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          waitingRequests.push({ resolve, reject })
        }).then(() => api(originalRequest))
      }

      originalRequest._retry = true
      isRefreshing = true
      const refreshToken = localStorage.getItem(REFRESH_KEY)

      try {
        if (!refreshToken) throw new Error('No refresh token')

        const response = await axios.post(
          `${API_BASE_URL}/auth/refresh`,
          {},
          { headers: { Authorization: `Bearer ${refreshToken}` } },
        )
        setTokens(response.data.data.access_token)
        waitingRequests.forEach((request) => request.resolve())
        waitingRequests = []
        return api(originalRequest)
      } catch (refreshError) {
        waitingRequests.forEach((request) => request.reject(refreshError))
        waitingRequests = []
        clearTokens()
        // Let the auth context / router react to the logout.
        window.dispatchEvent(new CustomEvent('emis:unauthorized'))
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  },
)

// ---------------------------------------------------------------------------
// Helpers used by the feature API modules
// ---------------------------------------------------------------------------
export function extractData(response) {
  // Backend responses look like { success, message, data, meta }.
  return response.data?.data
}

/**
 * Download a file from an authenticated endpoint.
 * A plain <a href> does not carry the Bearer token, so the API returns 401.
 * This uses the axios instance (which adds the token) and saves the blob.
 */
export async function downloadFile(url, fileName) {
  const response = await api.get(url, { responseType: 'blob' })
  const blobUrl = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = fileName || 'download'
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(blobUrl)
}

export function extractError(error) {
  if (error.response?.data?.message) return error.response.data.message
  if (error.response?.data?.errors) {
    const firstKey = Object.keys(error.response.data.errors)[0]
    const messages = error.response.data.errors[firstKey]
    return Array.isArray(messages) ? messages[0] : String(messages)
  }
  if (error.request) return 'Cannot reach the server. Check your connection.'
  return error.message || 'Something went wrong.'
}

export default api
