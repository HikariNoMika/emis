// Destination/source type for a station. Add a new entry here and in the
// backend STATION_TYPES to support a new source family.
export const STATION_TYPES = [
  { value: 'AWS', label: 'Automated Weather Station (AWS)' },
  { value: 'AWLS', label: 'Automated Water Level Station (AWLS)' },
]

export function stationTypeLabel(value) {
  return STATION_TYPES.find((type) => type.value === value)?.label || value || '—'
}

/** Match station names loosely: "Sto Niño" should find "Sto Nino, South Co". */
export function normalizeStationName(value) {
  return (value || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]/g, '')
}

export function findStationByName(stations, label) {
  const needle = normalizeStationName(label)
  if (!needle) return null
  return (stations || []).find((station) => {
    const value = normalizeStationName(station.name)
    return value === needle || value.startsWith(needle) || needle.startsWith(value)
  })
}
