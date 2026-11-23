import { useQuery } from '@tanstack/react-query'
import accomplishmentService from '../services/accomplishmentService'

export function useAccomplishmentSummary(year, quarter) {
  return useQuery({
    queryKey: ['accomplishment', 'summary', year, quarter],
    queryFn: () => accomplishmentService.summary(year, quarter),
  })
}

export function useAccomplishmentIndicators(params = {}) {
  return useQuery({
    queryKey: ['accomplishment', 'indicators', params],
    queryFn: () => accomplishmentService.indicators(params),
  })
}

export function useAccomplishmentTargets(params = {}) {
  return useQuery({
    queryKey: ['accomplishment', 'targets', params],
    queryFn: () => accomplishmentService.targets(params),
  })
}

export function useAccomplishmentActuals(params = {}) {
  return useQuery({
    queryKey: ['accomplishment', 'actuals', params],
    queryFn: () => accomplishmentService.actuals(params),
  })
}

export function useAccomplishmentWeights(year) {
  return useQuery({
    queryKey: ['accomplishment', 'weights', year],
    queryFn: () => accomplishmentService.weights(year),
  })
}

export function useAccomplishmentReports() {
  return useQuery({
    queryKey: ['accomplishment', 'reports'],
    queryFn: accomplishmentService.reports,
  })
}

export function useDataCompleteness(params = {}) {
  return useQuery({
    queryKey: ['accomplishment', 'completeness', params],
    queryFn: () => accomplishmentService.dataCompleteness(params),
  })
}
