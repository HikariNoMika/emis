import api, { clearTokens, extractData, setTokens } from './api'

export const authService = {
  async login(identifier, password) {
    const response = await api.post('/auth/login', { identifier, password })
    const data = extractData(response)
    setTokens(data.access_token, data.refresh_token)
    return data.user
  },

  async logout() {
    try {
      await api.post('/auth/logout')
    } finally {
      // Always clear local tokens, even if the server call fails.
      clearTokens()
    }
  },

  async me() {
    const response = await api.get('/auth/me')
    return extractData(response)
  },

  async changePassword(currentPassword, newPassword, confirmPassword) {
    const response = await api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword,
    })
    return response.data
  },
}

export default authService
