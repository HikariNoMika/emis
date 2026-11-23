import api, { downloadFile, extractData } from './api'

export const accomplishmentService = {
  async summary(year, quarter) {
    const params = quarter ? { year, quarter } : { year }
    return extractData(await api.get('/accomplishment/summary', { params }))
  },
  async quarterly(year, quarter) {
    return extractData(await api.get('/accomplishment/quarterly', { params: { year, quarter } }))
  },
  async annual(year) {
    return extractData(await api.get('/accomplishment/annual', { params: { year } }))
  },
  async dataCompleteness(params) {
    return extractData(await api.get('/accomplishment/data-completeness', { params }))
  },
  async categories() {
    return extractData(await api.get('/accomplishment/categories'))
  },
  async indicators(params = {}) {
    return extractData(await api.get('/accomplishment/indicators', { params }))
  },
  async createIndicator(payload) {
    return extractData(await api.post('/accomplishment/indicators', payload))
  },
  async updateIndicator(id, payload) {
    return extractData(await api.put(`/accomplishment/indicators/${id}`, payload))
  },
  async targets(params = {}) {
    return extractData(await api.get('/accomplishment/targets', { params }))
  },
  async createTarget(payload) {
    return extractData(await api.post('/accomplishment/targets', payload))
  },
  async updateTarget(id, payload) {
    return extractData(await api.put(`/accomplishment/targets/${id}`, payload))
  },
  async deleteTarget(id) {
    return extractData(await api.delete(`/accomplishment/targets/${id}`))
  },
  async actuals(params = {}) {
    return extractData(await api.get('/accomplishment/actuals', { params }))
  },
  async createActual(payload) {
    return extractData(await api.post('/accomplishment/actuals', payload))
  },
  async updateActual(id, payload) {
    return extractData(await api.put(`/accomplishment/actuals/${id}`, payload))
  },
  async deleteActual(id) {
    return extractData(await api.delete(`/accomplishment/actuals/${id}`))
  },
  async deleteIndicator(id) {
    return extractData(await api.delete(`/accomplishment/indicators/${id}`))
  },
  async weights(year) {
    return extractData(await api.get('/accomplishment/weights', { params: { year } }))
  },
  async saveWeights(payload) {
    return extractData(await api.put('/accomplishment/weights', payload))
  },
  async reports() {
    return extractData(await api.get('/accomplishment/reports'))
  },
  async generateReport(payload) {
    return extractData(await api.post('/accomplishment/reports/generate', payload))
  },
  async buildFile(id, fileFormat) {
    return extractData(await api.post(`/accomplishment/reports/${id}/file`, null, {
      params: { file_format: fileFormat },
    }))
  },
  async finalizeReport(id) {
    return extractData(await api.post(`/accomplishment/reports/${id}/finalize`))
  },
  async reviseReport(id, remarks) {
    return extractData(await api.post(`/accomplishment/reports/${id}/revise`, { remarks }))
  },
  async download(id, fileName) {
    await downloadFile(
      `/accomplishment/reports/${id}/download`,
      fileName || `accomplishment-report-${id}`,
    )
  },
  // Kept for compatibility; a plain <a href> cannot send the JWT.
  downloadUrl(id) {
    return `/api/v1/accomplishment/reports/${id}/download`
  },
}

export default accomplishmentService
