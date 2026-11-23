import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useStations } from '../../hooks/useStations'
import {
  Activity,
  AlertTriangle,
  Award,
  BarChart3,
  ChevronDown,
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
  Wrench,
} from 'lucide-react'

// `available: false` items are shown as disabled so the interface never
// presents a button that leads nowhere. They become links as phases complete.
const NAV_ITEMS = [
  { label: 'Dashboard', to: '/', icon: LayoutDashboard, available: true },
  { label: 'Station Map', to: '/map', icon: Map, available: true },
  { label: 'Stations', to: '/stations', icon: MapPin, available: true },
  { label: 'Sensor Management', to: '/sensors', icon: Radio, available: true },
  { label: 'Environmental Analytics', icon: BarChart3, available: true, dropdown: true },
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

export default function Sidebar({ collapsed, onToggle }) {
  const stationsQuery = useStations({ page: 1, per_page: 100 })
  const stations = stationsQuery.data?.data || []
  const [analyticsOpen, setAnalyticsOpen] = useState(false)
  const location = useLocation()
  const analyticsActive =
    location.pathname.startsWith('/analytics') ||
    /^\/stations\/\d+\/analytics/.test(location.pathname)

  return (
    <aside
      className={`flex h-full shrink-0 flex-col border-r border-brand-900 bg-brand-900 text-brand-100 transition-all duration-200 ${
        collapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Agency-style brand block */}
      <div className="flex h-16 items-center gap-3 border-b border-white/10 px-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-white/10 font-bold text-white">
          EM
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-white">EMIS</p>
            <p className="truncate text-[11px] text-brand-100/70">
              Environmental Monitoring
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
            return (
              <div key={item.label}>
                <button
                  type="button"
                  onClick={() => setAnalyticsOpen((open) => !open)}
                  className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm transition ${
                    analyticsActive
                      ? 'bg-brand-700 text-white'
                      : 'text-brand-100/80 hover:bg-white/10 hover:text-white'
                  }`}
                >
                  <Icon size={18} className="shrink-0" />
                  {!collapsed && (
                    <>
                      <span className="truncate">{item.label}</span>
                      <ChevronDown
                        size={14}
                        className={`ml-auto shrink-0 transition-transform ${
                          analyticsOpen ? 'rotate-180' : ''
                        }`}
                      />
                    </>
                  )}
                </button>

                {analyticsOpen && !collapsed && (
                  <div className="ml-4 mt-1 space-y-1 border-l border-white/10 pl-2">
                    <NavLink
                      to="/analytics"
                      className={({ isActive }) =>
                        `block rounded px-2 py-1.5 text-xs transition ${
                          isActive && location.pathname === '/analytics'
                            ? 'bg-brand-600 text-white'
                            : 'text-brand-100/70 hover:bg-white/10 hover:text-white'
                        }`
                      }
                    >
                      All stations
                    </NavLink>
                    {stations.map((station) => (
                      <NavLink
                        key={station.id}
                        to={`/stations/${station.id}/analytics`}
                        title={station.name}
                        className={({ isActive }) =>
                          `block rounded px-2 py-1.5 text-xs transition ${
                            isActive
                              ? 'bg-brand-600 text-white'
                              : 'text-brand-100/70 hover:bg-white/10 hover:text-white'
                          }`
                        }
                      >
                        <span className="block truncate">{station.name}</span>
                        <span className="block truncate text-[10px] text-brand-100/50">
                          {station.station_code}
                        </span>
                      </NavLink>
                    ))}
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
