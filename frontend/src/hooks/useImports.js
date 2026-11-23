import { useQuery } from '@tanstack/react-query'
import importService from '../services/importService'

export function useImports(params) {
  return useQuery({
    queryKey: ['imports', params],
    queryFn: () => importService.list(params),
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
