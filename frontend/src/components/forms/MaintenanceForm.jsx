import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { extractError } from '../../services/api'

const schema = z.object({
  station_id: z.coerce.number().int().min(1, 'Select a station'),
  sensor_id: z.preprocess(
    (value) => (value === '' || value == null ? null : Number(value)),
    z.number().int().nullable(),
  ),
  maintenance_type: z.enum(['ROUTINE', 'CORRECTIVE', 'CALIBRATION', 'REPLACEMENT', 'INSPECTION']),
  maintenance_date: z.string().min(1, 'Date is required'),
  performed_by: z.string().optional().or(z.literal('')),
  description: z.string().optional().or(z.literal('')),
  findings: z.string().optional().or(z.literal('')),
  action_taken: z.string().optional().or(z.literal('')),
  calibration_details: z.string().optional().or(z.literal('')),
  next_maintenance_date: z.string().optional().or(z.literal('')),
  remarks: z.string().optional().or(z.literal('')),
})

const TYPES = ['ROUTINE', 'CORRECTIVE', 'CALIBRATION', 'REPLACEMENT', 'INSPECTION']

function defaults(record, stations) {
  if (!record) {
    return {
      station_id: stations[0]?.id || '', sensor_id: '', maintenance_type: 'ROUTINE',
      maintenance_date: new Date().toISOString().slice(0, 10), performed_by: '',
      description: '', findings: '', action_taken: '', calibration_details: '',
      next_maintenance_date: '', remarks: '',
    }
  }
  return {
    ...record,
    sensor_id: record.sensor_id || '',
    maintenance_date: record.maintenance_date || '',
    next_maintenance_date: record.next_maintenance_date || '',
  }
}

export default function MaintenanceForm({ record, stations, sensors, onSubmit, onCancel, isWorking }) {
  const {
    register, handleSubmit, formState: { errors }, setError,
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: defaults(record, stations),
  })

  const submit = async (values) => {
    try {
      const payload = {
        ...values,
        performed_by: values.performed_by || null,
        description: values.description || null,
        findings: values.findings || null,
        action_taken: values.action_taken || null,
        calibration_details: values.calibration_details || null,
        next_maintenance_date: values.next_maintenance_date || null,
        remarks: values.remarks || null,
      }
      await onSubmit(payload)
    } catch (error) {
      setError('root', { message: extractError(error) })
    }
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-4">
      {errors.root && <div className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{errors.root.message}</div>}
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="label">Station</label>
          <select className="input" {...register('station_id')}>
            {stations.map((station) => <option key={station.id} value={station.id}>{station.name}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Sensor (optional)</label>
          <select className="input" {...register('sensor_id')}>
            <option value="">None</option>
            {sensors.map((sensor) => <option key={sensor.id} value={sensor.id}>{sensor.name}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Maintenance type</label>
          <select className="input" {...register('maintenance_type')}>
            {TYPES.map((type) => <option key={type}>{type}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Maintenance date</label>
          <input className="input" type="date" {...register('maintenance_date')} />
          {errors.maintenance_date && <p className="mt-1 text-xs text-red-600">{errors.maintenance_date.message}</p>}
        </div>
        <div>
          <label className="label">Performed by</label>
          <input className="input" {...register('performed_by')} />
        </div>
        <div>
          <label className="label">Next maintenance date</label>
          <input className="input" type="date" {...register('next_maintenance_date')} />
        </div>
      </div>
      {[
        ['description', 'Description'], ['findings', 'Findings'],
        ['action_taken', 'Action taken'], ['calibration_details', 'Calibration details'],
        ['remarks', 'Remarks'],
      ].map(([name, label]) => (
        <div key={name}>
          <label className="label">{label}</label>
          <textarea className="input" rows="2" {...register(name)} />
        </div>
      ))}
      <div className="flex justify-end gap-2 border-t border-slate-200 pt-4">
        <button type="button" className="btn-secondary" onClick={onCancel} disabled={isWorking}>Cancel</button>
        <button type="submit" className="btn-primary" disabled={isWorking}>
          {isWorking ? 'Saving…' : record ? 'Update record' : 'Create record'}
        </button>
      </div>
    </form>
  )
}
