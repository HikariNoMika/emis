import { useQuery } from '@tanstack/react-query'
import dashboardService from '../services/dashboardService'

// One small hook per API resource. React Query caches the results and gives us
// isLoading / isError / refetch for free.
export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: dashboardService.getSummary,
  })
}

export function useDataProgress(year) {
  return useQuery({
    queryKey: ['dashboard', 'data-progress', year],
    queryFn: () => dashboardService.getDataProgress(year),
    enabled: Boolean(year),
  })
}

export function useEnvironmentalSummary() {
  return useQuery({
    queryKey: ['dashboard', 'environmental-summary'],
    queryFn: dashboardService.getEnvironmentalSummary,
  })
}

export function useStationStatus() {
  return useQuery({
    queryKey: ['dashboard', 'station-status'],
    queryFn: dashboardService.getStationStatus,
  })
}

export function useRecentAlerts() {
  return useQuery({
    queryKey: ['dashboard', 'recent-alerts'],
    queryFn: dashboardService.getRecentAlerts,
  })
}
