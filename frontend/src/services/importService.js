import api, { downloadFile, extractData } from './api'

export const importService = {
  // FormData needs the multipart content type; the API client defaults to JSON.
  async upload(formData) {
    return extractData(
      await api.post('/imports/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 180000,
      }),
    )
  },

  async list(params = {}) {
    return (await api.get('/imports', { params })).data
  },

  async get(id) {
    return extractData(await api.get(`/imports/${id}`))
  },

  async preview(id, limit = 50) {
    return extractData(await api.get(`/imports/${id}/preview`, { params: { limit } }))
  },

  async updateMapping(id, payload) {
    return extractData(await api.put(`/imports/${id}/mapping`, payload))
  },

  async process(id) {
    return extractData(await api.post(`/imports/${id}/process`, {}, { timeout: 180000 }))
  },

  async reset(id) {
    return extractData(await api.post(`/imports/${id}/reset`))
  },

  async errors(id) {
    return extractData(await api.get(`/imports/${id}/errors`))
  },

  async progress(id) {
    return extractData(await api.get(`/imports/${id}/progress`))
  },

  async downloadSource(id, fileName) {
    await downloadFile(`/imports/${id}/file`, fileName)
  },
}

export default importService
