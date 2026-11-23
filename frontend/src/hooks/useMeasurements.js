import { useQuery } from '@tanstack/react-query'
import measurementService from '../services/measurementService'

export function useLatestMeasurements(params = {}) {
  return useQuery({
    queryKey: ['measurements', 'latest', params],
    queryFn: () => measurementService.latest(params),
  })
}

export function useTrends(params) {
  return useQuery({
    queryKey: ['measurements', 'trends', params],
    queryFn: () => measurementService.trends(params),
    enabled: Boolean(params.station_id && params.measurement_type_ids?.length),
  })
}

export function useFlexibleComparison(params) {
  return useQuery({
    queryKey: ['measurements', 'flexible-comparison', params],
    queryFn: () => measurementService.compareFlexible(params),
    enabled: Boolean(
      params.station_id && params.measurement_type_id &&
      params.date_from_a && params.date_to_a &&
      params.date_from_b && params.date_to_b,
    ),
  })
}

export function useStatistics(params) {
  return useQuery({
    queryKey: ['measurements', 'statistics', params],
    queryFn: () => measurementService.statistics(params),
    enabled: Boolean(params.measurement_type_id),
  })
}

export function useComparison(params) {
  return useQuery({
    queryKey: ['analytics', 'comparison', params],
    queryFn: () => measurementService.comparison(params),
    enabled: Boolean(params.measurement_type_id && params.station_ids?.length),
  })
}
