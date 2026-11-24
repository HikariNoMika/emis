import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { extractError } from '../../services/api'
import { STATION_TYPES } from '../../utils/stations'

const optionalNumber = z.preprocess(
  (value) => (value === '' || value === null || value === undefined ? undefined : Number(value)),
  z.number({ invalid_type_error: 'Must be a number' }).optional(),
)

const stationSchema = z.object({
  station_code: z.string().min(1, 'Station code is required').max(50),
  name: z.string().min(1, 'Station name is required').max(150),
  station_type: z.enum(['AWS', 'AWLS']),
  site_name: z.string().max(150).optional().or(z.literal('')),
  description: z.string().optional().or(z.literal('')),
  latitude: optionalNumber.refine((v) => v === undefined || (v >= -90 && v <= 90), 'Must be between -90 and 90'),
  longitude: optionalNumber.refine((v) => v === undefined || (v >= -180 && v <= 180), 'Must be between -180 and 180'),
  elevation: optionalNumber,
  timezone: z.string().min(1).max(64),
  measurement_interval_seconds: z.coerce.number().int().min(1).max(86400),
  installation_date: z.string().optional().or(z.literal('')),
  operational_status: z.enum(['ONLINE', 'DELAYED', 'OFFLINE', 'MAINTENANCE', 'UNKNOWN']),
  device_serial_number: z.string().max(100).optional().or(z.literal('')),
  remarks: z.string().optional().or(z.literal('')),
})

const STATUSES = ['ONLINE', 'DELAYED', 'OFFLINE', 'MAINTENANCE', 'UNKNOWN']

function buildDefaults(station) {
  if (!station) {
    return {
      station_code: '', name: '', station_type: 'AWS', site_name: '', description: '',
      latitude: '', longitude: '', elevation: '', timezone: 'Asia/Manila',
      measurement_interval_seconds: 900, installation_date: '',
      operational_status: 'UNKNOWN', device_serial_number: '', remarks: '',
    }
  }
  return {
    station_code: station.station_code || '',
    name: station.name || '',
    station_type: station.station_type || 'AWS',
    site_name: station.site_name || '',
    description: station.description || '',
    latitude: station.latitude ?? '',
    longitude: station.longitude ?? '',
    elevation: station.elevation ?? '',
    timezone: station.timezone || 'Asia/Manila',
    measurement_interval_seconds: station.measurement_interval_seconds ?? 900,
    installation_date: station.installation_date || '',
    operational_status: station.operational_status || 'UNKNOWN',
    device_serial_number: station.device_serial_number || '',
    remarks: station.remarks || '',
  }
}

export default function StationForm({ station, onSubmit, onCancel, isWorking = false, submitLabel = 'Save station' }) {
  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm({
    resolver: zodResolver(stationSchema),
    defaultValues: buildDefaults(station),
  })

  const submit = async (values) => {
    try {
      // Empty optional strings become null so the API stores clean values.
      const payload = {
        ...values,
        site_name: values.site_name || null,
        description: values.description || null,
        installation_date: values.installation_date || null,
        device_serial_number: values.device_serial_number || null,
        remarks: values.remarks || null,
      }
      await onSubmit(payload)
    } catch (error) {
      setError('root', { message: extractError(error) })
    }
  }

  const field = (name, label, props = {}) => (
    <div>
      <label className="label" htmlFor={name}>{label}</label>
      <input id={name} className="input" {...register(name)} {...props} />
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
        {field('station_code', 'Station code', { placeholder: '06-02478', disabled: Boolean(station) })}
        {field('name', 'Station name', { placeholder: 'Salacafe' })}
        <div>
          <label className="label" htmlFor="station_type">Destination type</label>
          <select id="station_type" className="input" {...register('station_type')}>
            {STATION_TYPES.map((type) => (
              <option key={type.value} value={type.value}>{type.label}</option>
            ))}
          </select>
          {errors.station_type && <p className="mt-1 text-xs text-red-600">{errors.station_type.message}</p>}
        </div>
        {field('site_name', 'Site name', { placeholder: 'DENRFMB-WATERSHED' })}
        {field('device_serial_number', 'Device serial number', { placeholder: '929' })}
        {field('latitude', 'Latitude', { step: 'any', placeholder: '6.11582' })}
        {field('longitude', 'Longitude', { step: 'any', placeholder: '124.846231' })}
        {field('elevation', 'Elevation (m)', { step: 'any' })}
        {field('timezone', 'Timezone', { placeholder: 'Asia/Manila' })}
        {field('measurement_interval_seconds', 'Measurement interval (seconds)', { type: 'number' })}
        {field('installation_date', 'Installation date', { type: 'date' })}
        <div>
          <label className="label" htmlFor="operational_status">Operational status</label>
          <select id="operational_status" className="input" {...register('operational_status')}>
            {STATUSES.map((status) => <option key={status}>{status}</option>)}
          </select>
          {errors.operational_status && <p className="mt-1 text-xs text-red-600">{errors.operational_status.message}</p>}
        </div>
      </div>

      <div>
        <label className="label" htmlFor="description">Description</label>
        <textarea id="description" rows="3" className="input" {...register('description')} />
      </div>
      <div>
        <label className="label" htmlFor="remarks">Remarks</label>
        <textarea id="remarks" rows="2" className="input" {...register('remarks')} />
      </div>

      <div className="flex justify-end gap-2 border-t border-slate-200 pt-4">
        <button type="button" className="btn-secondary" onClick={onCancel} disabled={isWorking}>
          Cancel
        </button>
        <button type="submit" className="btn-primary" disabled={isWorking}>
          {isWorking ? 'Saving…' : submitLabel}
        </button>
      </div>
    </form>
  )
}
