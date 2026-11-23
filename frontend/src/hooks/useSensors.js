import { useQuery } from '@tanstack/react-query'
import measurementTypeService from '../services/measurementTypeService'
import sensorService from '../services/sensorService'

export function useSensors(params) {
  return useQuery({
    queryKey: ['sensors', params],
    queryFn: () => sensorService.list(params),
  })
}

export function useSensor(sensorId) {
  return useQuery({
    queryKey: ['sensors', sensorId],
    queryFn: () => sensorService.get(sensorId),
    enabled: Boolean(sensorId),
  })
}

export function useSensorHealth(sensorId) {
  return useQuery({
    queryKey: ['sensors', sensorId, 'health'],
    queryFn: () => sensorService.health(sensorId),
    enabled: Boolean(sensorId),
  })
}

export function useSensorMeasurements(sensorId, params = {}) {
  return useQuery({
    queryKey: ['sensors', sensorId, 'measurements', params],
    queryFn: () => sensorService.measurements(sensorId, params),
    enabled: Boolean(sensorId),
  })
}

export function useMeasurementTypes() {
  return useQuery({
    queryKey: ['measurement-types'],
    queryFn: measurementTypeService.list,
    staleTime: 5 * 60 * 1000,
  })
}
