import api, { extractData } from './api'

export const userService = {
  async list(params = {}) {
    return (await api.get('/users', { params })).data
  },

  async create(payload) {
    return extractData(await api.post('/users', payload))
  },

  async update(id, payload) {
    return extractData(await api.put(`/users/${id}`, payload))
  },

  async setActive(id, active) {
    return extractData(await api.post(`/users/${id}/${active ? 'activate' : 'deactivate'}`))
  },

  async resetPassword(id, payload) {
    return extractData(await api.post(`/users/${id}/reset-password`, payload))
  },

  async updateProfile(payload) {
    return extractData(await api.put('/auth/profile', payload))
  },
}

export default userService
