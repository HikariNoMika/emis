import api, { extractData } from './api'

export const stationService = {
  // The list response includes pagination metadata, so keep the full envelope.
  async list(params = {}) {
    return (await api.get('/stations', { params })).data
  },

  async get(id) {
    return extractData(await api.get(`/stations/${id}`))
  },

  async create(payload) {
    return extractData(await api.post('/stations', payload))
  },

  async update(id, payload) {
    return extractData(await api.put(`/stations/${id}`, payload))
  },

  async archive(id) {
    return (await api.delete(`/stations/${id}`)).data
  },

  async mapData() {
    return extractData(await api.get('/stations/map-data'))
  },

  async sensors(id) {
    return extractData(await api.get(`/stations/${id}/sensors`))
  },

  async measurements(id, params = {}) {
    return (await api.get(`/stations/${id}/measurements`, { params })).data
  },

  async status(id) {
    return extractData(await api.get(`/stations/${id}/status`))
  },

  async maintenance(id) {
    return extractData(await api.get(`/stations/${id}/maintenance`))
  },

  async imports(id) {
    return extractData(await api.get(`/stations/${id}/imports`))
  },

  async history(id) {
    return extractData(await api.get(`/stations/${id}/history`))
  },
}

export default stationService
