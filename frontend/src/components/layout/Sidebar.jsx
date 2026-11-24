import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useStations } from '../../hooks/useStations'
import { findStationByName } from '../../utils/stations'
import {
  Activity,
  AlertTriangle,
  Award,
  ChevronDown,
  CloudSun,
  ChevronLeft,
  ClipboardList,
  Database,
  FileBarChart,
  GitCompare,
  LayoutDashboard,
  Map,
  MapPin,
  Radio,
  Settings,
  ShieldCheck,
  Users,
  Waves,
  Wrench,
} from 'lucide-react'

// `available: false` items are shown as disabled so the interface never
// presents a button that leads nowhere. They become links as phases complete.
const NAV_ITEMS = [
  { label: 'Dashboard', to: '/', icon: LayoutDashboard, available: true },
  { label: 'Station Map', to: '/map', icon: Map, available: true },
  { label: 'Stations', to: '/stations', icon: MapPin, available: true },
  { label: 'Sensor Management', to: '/sensors', icon: Radio, available: true },
  {
    label: 'Automated Water Level Station (AWLS)',
    icon: Waves,
    available: true,
    dropdown: 'awls',
  },
  {
    label: 'Automated Weather Station (AWS)',
    icon: CloudSun,
    available: true,
    dropdown: 'aws',
  },
  { label: 'Latest Monitoring', to: '/latest', icon: Activity, available: true },
  { label: 'Station Health', to: '/health', icon: ShieldCheck, available: true },
  { label: 'Data Quality', to: '/data-quality', icon: ClipboardList, available: true },
  { label: 'Alerts', to: '/alerts', icon: AlertTriangle, available: true },
  { label: 'Data Management', to: '/data-management', icon: Database, available: true },
  { label: 'Station Comparison', to: '/comparison', icon: GitCompare, available: true },
  { label: 'Reports', to: '/reports', icon: FileBarChart, available: true },
  { label: 'Maintenance', to: '/maintenance', icon: Wrench, available: true },
  { label: 'Quarterly Accomplishment', to: '/accomplishment', icon: Award, available: true },
  { label: 'Audit Logs', to: '/audit-logs', icon: ClipboardList, available: true },
  { label: 'User Management', to: '/users', icon: Users, available: true },
  { label: 'System Settings', to: '/settings', icon: Settings, available: true },
]

// The three AWS sites. Stations are created from workbook metadata during an
// import, so a site is only linked once it actually exists in the database.
const AWS_STATIONS = ['Salacafe', 'Lake Sebu', 'Sto Niño']

export default function Sidebar({ collapsed, onToggle }) {
  const stationsQuery = useStations({ page: 1, per_page: 100 })
  const stations = stationsQuery.data?.data || []
  const [awsOpen, setAwsOpen] = useState(false)
  const [awlsOpen, setAwlsOpen] = useState(false)
  const location = useLocation()
  const awsActive = location.pathname.startsWith('/aws')
  const awlsActive = location.pathname.startsWith('/awls')

  return (
    <aside
      className={`flex h-full shrink-0 flex-col border-r border-brand-900 bg-brand-900 text-brand-100 transition-all duration-200 ${
        collapsed ? 'w-16' : 'w-80'
      }`}
    >
      {/* Agency-style brand block */}
      <div className="flex h-16 items-center gap-3 border-b border-white/10 px-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-white/10 font-bold text-white">
          PW
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-white">PFMS Watershed</p>
            <p className="truncate text-[11px] text-brand-100/70">
              Watershed Monitoring
            </p>
          </div>
        )}
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-2 py-4">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          if (!item.available) {
            return (
              <div
                key={item.label}
                title={`Planned for Phase ${item.phase}`}
                className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-brand-100/40"
              >
                <Icon size={18} className="shrink-0" />
                {!collapsed && (
                  <>
                    <span className="truncate">{item.label}</span>
                    <span className="ml-auto text-[10px] uppercase tracking-wide">
                      Soon
                    </span>
                  </>
                )}
              </div>
            )
          }

          if (item.dropdown) {
            const isAwls = item.dropdown === 'awls'
            const isAws = !isAwls
            const isOpen = isAwls ? awlsOpen : awsOpen
            const toggle = isAwls
              ? () => setAwlsOpen((open) => !open)
              : () => setAwsOpen((open) => !open)
            const active = isAwls ? awlsActive : awsActive
            const namnama = findStationByName(stations, 'NAMNAMA')

            return (
              <div key={item.label}>
                <button
                  type="button"
                  onClick={toggle}
                  className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm transition ${
                    active
                      ? 'bg-brand-700 text-white'
                      : 'text-brand-100/80 hover:bg-white/10 hover:text-white'
                  }`}
                >
                  <Icon size={18} className="shrink-0" />
                  {!collapsed && (
                    <>
                      <span className="leading-tight">{item.label}</span>
                      <ChevronDown
                        size={14}
                        className={`ml-auto shrink-0 transition-transform ${
                          isOpen ? 'rotate-180' : ''
                        }`}
                      />
                    </>
                  )}
                </button>

                {isOpen && !collapsed && (
                  <div className="ml-4 mt-1 space-y-1 border-l border-white/10 pl-2">
                    {isAws ? (
                      AWS_STATIONS.map((name) => {
                        const station = findStationByName(stations, name)
                        return (
                          <NavLink
                            key={name}
                            to={
                              station
                                ? `/aws/${station.id}`
                                : `/aws/new?name=${encodeURIComponent(name)}`
                            }
                            title={station ? station.name : `Upload data for ${name}`}
                            className={({ isActive }) =>
                              `block rounded px-2 py-1.5 text-xs transition ${
                                isActive
                                  ? 'bg-brand-600 text-white'
                                  : 'text-brand-100/70 hover:bg-white/10 hover:text-white'
                              }`
                            }
                          >
                            <span className="block truncate">{name}</span>
                            <span className="block truncate text-[10px] text-brand-100/50">
                              {station ? station.station_code : 'Upload data →'}
                            </span>
                          </NavLink>
                        )
                      })
                    ) : !namnama ? (
                      <div
                        title="Upload a water-level CSV for NAMNAMA from Data Management."
                        className="rounded px-2 py-1.5 text-xs text-brand-100/40"
                      >
                        <span className="block truncate">NAMNAMA</span>
                        <span className="block truncate text-[10px] text-brand-100/30">
                          Awaiting import
                        </span>
                      </div>
                    ) : (
                      <NavLink
                        to="/awls"
                        title={namnama.name}
                        className={({ isActive }) =>
                          `block rounded px-2 py-1.5 text-xs transition ${
                            isActive
                              ? 'bg-brand-600 text-white'
                              : 'text-brand-100/70 hover:bg-white/10 hover:text-white'
                          }`
                        }
                      >
                        <span className="block truncate">NAMNAMA</span>
                        <span className="block truncate text-[10px] text-brand-100/50">
                          {namnama.station_code}
                        </span>
                      </NavLink>
                    )}
                  </div>
                )}
              </div>
            )
          }

          return (
            <NavLink
              key={item.label}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition ${
                  isActive
                    ? 'bg-brand-600 text-white'
                    : 'text-brand-100/80 hover:bg-white/10 hover:text-white'
                }`
              }
            >
              <Icon size={18} className="shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </NavLink>
          )
        })}
      </nav>

      <button
        type="button"
        onClick={onToggle}
        className="flex h-12 items-center gap-3 border-t border-white/10 px-4 text-sm text-brand-100/70 hover:bg-white/5 hover:text-white"
      >
        <ChevronLeft
          size={18}
          className={`shrink-0 transition-transform ${collapsed ? 'rotate-180' : ''}`}
        />
        {!collapsed && <span>Collapse sidebar</span>}
      </button>
    </aside>
  )
}
