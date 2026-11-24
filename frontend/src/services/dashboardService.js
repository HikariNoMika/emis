import api, { extractData } from './api'

export const dashboardService = {
  async getSummary() {
    return extractData(await api.get('/dashboard/summary'))
  },

  async getDataProgress(year) {
    return extractData(await api.get('/dashboard/data-progress', { params: { year } }))
  },

  async getEnvironmentalSummary() {
    return extractData(await api.get('/dashboard/environmental-summary'))
  },

  async getStationStatus() {
    return extractData(await api.get('/dashboard/station-status'))
  },

  async getRecentAlerts() {
    return extractData(await api.get('/dashboard/recent-alerts'))
  },

  async getSystemSettings() {
    return extractData(await api.get('/system/settings'))
  },

  async saveSetting(payload) {
    return extractData(await api.put('/system/settings', payload))
  },

  async getAuditLogs(params = {}) {
    // Return the full envelope because audit logs include pagination `meta`.
    return (await api.get('/audit-logs', { params })).data
  },
}

export default dashboardService
