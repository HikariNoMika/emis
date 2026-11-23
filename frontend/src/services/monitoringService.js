import api, { extractData } from './api'

export const dataQualityService = {
  async summary() {
    return extractData(await api.get('/data-quality/summary'))
  },
  async flags(params = {}) {
    return (await api.get('/data-quality/flags', { params })).data
  },
  async resolve(id, payload) {
    return extractData(await api.post(`/data-quality/flags/${id}/resolve`, payload))
  },
}

export const alertService = {
  async list(params = {}) {
    return (await api.get('/alerts', { params })).data
  },
  async acknowledge(id, remarks) {
    return extractData(await api.post(`/alerts/${id}/acknowledge`, { remarks }))
  },
  async resolve(id, remarks) {
    return extractData(await api.post(`/alerts/${id}/resolve`, { remarks }))
  },
  async history(id) {
    return extractData(await api.get(`/alerts/${id}/history`))
  },
}

export const healthService = {
  async stations() {
    return extractData(await api.get('/health/stations'))
  },
  async refresh(stationId) {
    const params = stationId ? { station_id: stationId } : {}
    return extractData(await api.post('/health/refresh', {}, { params }))
  },
}
