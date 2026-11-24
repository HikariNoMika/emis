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
