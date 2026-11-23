import { useQuery } from '@tanstack/react-query'
import stationService from '../services/stationService'

export function useStations(params) {
  return useQuery({
    queryKey: ['stations', params],
    queryFn: () => stationService.list(params),
  })
}

export function useMapStations() {
  return useQuery({
    queryKey: ['stations', 'map-data'],
    queryFn: stationService.mapData,
  })
}

export function useStation(stationId) {
  return useQuery({
    queryKey: ['stations', stationId],
    queryFn: () => stationService.get(stationId),
    enabled: Boolean(stationId),
  })
}

export function useStationRelated(stationId, kind, params = {}) {
  return useQuery({
    queryKey: ['stations', stationId, kind, params],
    queryFn: () => {
      if (kind === 'sensors') return stationService.sensors(stationId).then((data) => ({ data }))
      if (kind === 'measurements') return stationService.measurements(stationId, params)
      if (kind === 'status') return stationService.status(stationId).then((data) => ({ data }))
      if (kind === 'maintenance') return stationService.maintenance(stationId).then((data) => ({ data }))
      if (kind === 'imports') return stationService.imports(stationId).then((data) => ({ data }))
      if (kind === 'history') return stationService.history(stationId).then((data) => ({ data }))
      return Promise.resolve({ data: [] })
    },
    enabled: Boolean(stationId),
  })
}
