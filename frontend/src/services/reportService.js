import api, { downloadFile, extractData } from './api'

export const reportService = {
  async list(params = {}) {
    return (await api.get('/reports', { params })).data
  },

  async generate(payload) {
    return extractData(await api.post('/reports/generate', payload))
  },

  async progress(jobId) {
    return extractData(await api.get(`/reports/progress/${jobId}`))
  },

  async get(id) {
    return extractData(await api.get(`/reports/${id}`))
  },

  async download(id, fileName) {
    await downloadFile(`/reports/${id}/download`, fileName || `report-${id}`)
  },
  // Kept for compatibility, but do not use as an <a href>: it cannot send the JWT.
  downloadUrl(id) {
    return `/api/v1/reports/${id}/download`
  },
}

export default reportService
