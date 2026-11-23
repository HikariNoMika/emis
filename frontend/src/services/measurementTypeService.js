import api, { extractData } from './api'

export const measurementTypeService = {
  async list() {
    return extractData(await api.get('/measurement-types'))
  },

  async create(payload) {
    return extractData(await api.post('/measurement-types', payload))
  },

  async update(id, payload) {
    return extractData(await api.put(`/measurement-types/${id}`, payload))
  },
}

export default measurementTypeService
