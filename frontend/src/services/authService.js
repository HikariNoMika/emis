import api, { clearTokens, extractData, setTokens } from './api'

export const authService = {
  async login(identifier, password) {
    const response = await api.post('/auth/login', { identifier, password })
    const data = extractData(response)
    if (data.mfa_required) {
      return { mfaRequired: true, mfaToken: data.mfa_token }
    }
    setTokens(data.access_token, data.refresh_token)
    return data.user
  },

  async verifyMfa(mfaToken, code) {
    const response = await api.post('/auth/mfa/verify', { mfa_token: mfaToken, code })
    const data = extractData(response)
    setTokens(data.access_token, data.refresh_token)
    return data.user
  },

  async mfaSetup() {
    return extractData(await api.post('/auth/mfa/setup'))
  },

  async mfaEnable(code) {
    return extractData(await api.post('/auth/mfa/enable', { code }))
  },

  async mfaDisable(password, code) {
    return extractData(await api.post('/auth/mfa/disable', { password, code }))
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
    return extractData(response)
  },
}

export default authService
