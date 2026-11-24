import { useQuery } from '@tanstack/react-query'
import importService from '../services/importService'

export function useImports(params) {
  return useQuery({
    queryKey: ['imports', params],
    queryFn: () => importService.list(params),
  })
}

export function useImportProgress(batchId, enabled = false) {
  return useQuery({
    queryKey: ['imports', batchId, 'progress'],
    queryFn: () => importService.progress(batchId),
    enabled: Boolean(batchId) && enabled,
    refetchInterval: enabled ? 1000 : false,
    retry: false,
  })
}

export function useStationImports(stationId) {
  return useQuery({
    queryKey: ['imports', { station_id: stationId }],
    queryFn: () => importService.list({ station_id: stationId, per_page: 50 }),
    enabled: Boolean(stationId),
  })
}

export function useImportPreview(batchId) {
  return useQuery({
    queryKey: ['imports', batchId, 'preview'],
    queryFn: () => importService.preview(batchId),
    enabled: Boolean(batchId),
  })
}

export function useImportErrors(batchId) {
  return useQuery({
    queryKey: ['imports', batchId, 'errors'],
    queryFn: () => importService.errors(batchId),
    enabled: Boolean(batchId),
  })
}
