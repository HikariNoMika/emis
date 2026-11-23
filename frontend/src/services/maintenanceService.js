import api, { extractData } from './api'

export const maintenanceService = {
  async list(params = {}) {
    return (await api.get('/maintenance', { params })).data
  },
  async calendar() {
    return extractData(await api.get('/maintenance/calendar'))
  },
  async create(payload) {
    return extractData(await api.post('/maintenance', payload))
  },
  async update(id, payload) {
    return extractData(await api.put(`/maintenance/${id}`, payload))
  },
  async remove(id) {
    return (await api.delete(`/maintenance/${id}`)).data
  },
}

export default maintenanceService
