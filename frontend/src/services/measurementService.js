import api, { downloadFile, extractData } from './api'

export const measurementService = {
  async latest(params = {}) {
    return extractData(await api.get('/measurements/latest', { params }))
  },

  async trends(params) {
    return extractData(await api.get('/measurements/trends', { params }))
  },

  async statistics(params) {
    return extractData(await api.get('/measurements/statistics', { params }))
  },

  async list(params = {}) {
    return (await api.get('/measurements', { params })).data
  },

  async comparison(params) {
    return extractData(await api.get('/analytics/comparison', { params }))
  },

  async statisticsBulk(stationId, dateFrom, dateTo) {
    const params = { station_id: stationId }
    if (dateFrom) params.date_from = dateFrom
    if (dateTo) params.date_to = dateTo
    return extractData(await api.get('/measurements/statistics/bulk', { params }))
  },

  async compareFlexible(params) {
    return extractData(await api.get('/measurements/compare-flexible', { params }))
  },

  async exportFile(params, fileName) {
    const query = new URLSearchParams(params).toString()
    await downloadFile(`/measurements/export?${query}`, fileName || 'emis-export')
  },
  // Kept for compatibility; a plain <a href> cannot send the JWT.
  exportUrl(params) {
    const query = new URLSearchParams(params).toString()
    return `/api/v1/measurements/export?${query}`
  },
}

export default measurementService
