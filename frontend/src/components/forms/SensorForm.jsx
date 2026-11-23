import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { extractError } from '../../services/api'

const sensorSchema = z.object({
  station_id: z.coerce.number().int().min(1, 'Select a station'),
  port_number: z.string().max(20).optional().or(z.literal('')),
  name: z.string().min(1, 'Sensor name is required').max(150),
  model: z.string().max(100).optional().or(z.literal('')),
  manufacturer: z.string().max(100).optional().or(z.literal('')),
  serial_number: z.string().max(100).optional().or(z.literal('')),
  installation_date: z.string().optional().or(z.literal('')),
  calibration_date: z.string().optional().or(z.literal('')),
  next_calibration_date: z.string().optional().or(z.literal('')),
  operational_status: z.enum(['ACTIVE', 'INACTIVE', 'FAULTY', 'MAINTENANCE', 'UNKNOWN']),
  description: z.string().optional().or(z.literal('')),
})

const STATUSES = ['ACTIVE', 'INACTIVE', 'FAULTY', 'MAINTENANCE', 'UNKNOWN']

function buildDefaults(sensor, defaultStationId) {
  if (!sensor) {
    return {
      station_id: defaultStationId || '', port_number: '', name: '', model: '',
      manufacturer: '', serial_number: '', installation_date: '', calibration_date: '',
      next_calibration_date: '', operational_status: 'ACTIVE', description: '',
    }
  }
  return {
    station_id: sensor.station_id,
    port_number: sensor.port_number || '',
    name: sensor.name || '',
    model: sensor.model || '',
    manufacturer: sensor.manufacturer || '',
    serial_number: sensor.serial_number || '',
    installation_date: sensor.installation_date || '',
    calibration_date: sensor.calibration_date || '',
    next_calibration_date: sensor.next_calibration_date || '',
    operational_status: sensor.operational_status || 'ACTIVE',
    description: sensor.description || '',
  }
}

export default function SensorForm({
  sensor,
  stations = [],
  defaultStationId,
  onSubmit,
  onCancel,
  isWorking = false,
}) {
  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm({
    resolver: zodResolver(sensorSchema),
    defaultValues: buildDefaults(sensor, defaultStationId),
  })

  const submit = async (values) => {
    try {
      const payload = {
        ...values,
        port_number: values.port_number || null,
        model: values.model || null,
        manufacturer: values.manufacturer || null,
        serial_number: values.serial_number || null,
        installation_date: values.installation_date || null,
        calibration_date: values.calibration_date || null,
        next_calibration_date: values.next_calibration_date || null,
        description: values.description || null,
      }
      await onSubmit(payload)
    } catch (error) {
      setError('root', { message: extractError(error) })
    }
  }

  const field = (name, label, props = {}) => (
    <div>
      <label className="label" htmlFor={`sensor-${name}`}>{label}</label>
      <input id={`sensor-${name}`} className="input" {...register(name)} {...props} />
      {errors[name] && <p className="mt-1 text-xs text-red-600">{errors[name].message}</p>}
    </div>
  )

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-4">
      {errors.root && (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {errors.root.message}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="label" htmlFor="sensor-station">Station</label>
          <select id="sensor-station" className="input" {...register('station_id')} disabled={Boolean(sensor)}>
            <option value="">Select a station…</option>
            {stations.map((station) => (
              <option key={station.id} value={station.id}>
                {station.station_code} — {station.name}
              </option>
            ))}
          </select>
          {errors.station_id && <p className="mt-1 text-xs text-red-600">{errors.station_id.message}</p>}
        </div>
        {field('port_number', 'Port number', { placeholder: '1' })}
        {field('name', 'Sensor name', { placeholder: 'VP-4 Weather Sensor' })}
        {field('model', 'Model', { placeholder: 'VP-4' })}
        {field('manufacturer', 'Manufacturer')}
        {field('serial_number', 'Serial number')}
        {field('installation_date', 'Installation date', { type: 'date' })}
        {field('calibration_date', 'Calibration date', { type: 'date' })}
        {field('next_calibration_date', 'Next calibration date', { type: 'date' })}
        <div>
          <label className="label" htmlFor="sensor-status">Operational status</label>
          <select id="sensor-status" className="input" {...register('operational_status')}>
            {STATUSES.map((status) => <option key={status}>{status}</option>)}
          </select>
        </div>
      </div>

      <div>
        <label className="label" htmlFor="sensor-description">Description</label>
        <textarea id="sensor-description" rows="3" className="input" {...register('description')} />
      </div>

      <div className="flex justify-end gap-2 border-t border-slate-200 pt-4">
        <button type="button" className="btn-secondary" onClick={onCancel} disabled={isWorking}>Cancel</button>
        <button type="submit" className="btn-primary" disabled={isWorking}>
          {isWorking ? 'Saving…' : sensor ? 'Update sensor' : 'Create sensor'}
        </button>
      </div>
    </form>
  )
}
