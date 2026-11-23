import api, { extractData } from './api'

export const sensorService = {
  async list(params = {}) {
    return (await api.get('/sensors', { params })).data
  },

  async get(id) {
    return extractData(await api.get(`/sensors/${id}`))
  },

  async create(payload) {
    return extractData(await api.post('/sensors', payload))
  },

  async update(id, payload) {
    return extractData(await api.put(`/sensors/${id}`, payload))
  },

  async setMeasurementTypes(id, payload) {
    return extractData(await api.put(`/sensors/${id}/measurement-types`, payload))
  },

  async health(id) {
    return extractData(await api.get(`/sensors/${id}/health`))
  },

  async measurements(id, params = {}) {
    return (await api.get(`/sensors/${id}/measurements`, { params })).data
  },
}

export default sensorService
