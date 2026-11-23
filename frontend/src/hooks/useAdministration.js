import { useQuery } from '@tanstack/react-query'
import dashboardService from '../services/dashboardService'
import maintenanceService from '../services/maintenanceService'
import reportService from '../services/reportService'

export function useReports(params) {
  return useQuery({
    queryKey: ['reports', params],
    queryFn: () => reportService.list(params),
  })
}

export function useMaintenance(params) {
  return useQuery({
    queryKey: ['maintenance', params],
    queryFn: () => maintenanceService.list(params),
  })
}

export function useMaintenanceCalendar() {
  return useQuery({
    queryKey: ['maintenance', 'calendar'],
    queryFn: maintenanceService.calendar,
  })
}

export function useSystemSettings() {
  return useQuery({
    queryKey: ['system', 'settings'],
    queryFn: dashboardService.getSystemSettings,
  })
}
