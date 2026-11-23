import { useQuery } from '@tanstack/react-query'
import {
  alertService,
  dataQualityService,
  healthService,
} from '../services/monitoringService'

export function useQualitySummary() {
  return useQuery({
    queryKey: ['quality', 'summary'],
    queryFn: dataQualityService.summary,
  })
}

export function useQualityFlags(params) {
  return useQuery({
    queryKey: ['quality', 'flags', params],
    queryFn: () => dataQualityService.flags(params),
  })
}

export function useAlerts(params) {
  return useQuery({
    queryKey: ['alerts', params],
    queryFn: () => alertService.list(params),
  })
}

export function useStationHealth() {
  return useQuery({
    queryKey: ['health', 'stations'],
    queryFn: healthService.stations,
  })
}
