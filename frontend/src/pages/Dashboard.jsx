import React, { useState, useEffect } from 'react'
import {
  BarChart2, Database, Cpu, Activity,
  CheckCircle2, XCircle, Loader2,
  ChevronRight, Layers, Zap, Globe
} from 'lucide-react'
import Chat from '../components/Chat.jsx'
import { getHealth, getDatasetInfo, getSuggestions } from '../api.js'

/* ── Status badge ──────────────────────────── */
function StatusBadge({ status }) {
  if (status === 'loading') return (
    <div className="flex items-center gap-1.5 text-dim text-xs font-medium">
      <Loader2 size={11} className="animate-spin" />
      Connecting...
    </div>
  )
  if (status === 'ok') return (
    <div className="flex items-center gap-1.5 text-sage text-xs font-medium bg-sage/10 px-2 py-0.5 rounded-full">
      <div className="w-1.5 h-1.5 rounded-full bg-sage animate-pulse" />
      System Online
    </div>
  )
  return (
    <div className="flex items-center gap-1.5 text-rose text-xs font-medium bg-rose/10 px-2 py-0.5 rounded-full">
      <div className="w-1.5 h-1.5 rounded-full bg-rose" />
      Offline
    </div>
  )
}

/* ── Stat card ─────────────────────────────── */
function StatCard({ label, value, icon: Icon, color = 'text-accent', delay = 0 }) {
  return (
    <div
      className="bg-card border border-border rounded-2xl p-4 shadow-soft animate-fade-up hover:shadow-card transition-shadow"
      style={{ animationDelay: `${delay}ms`, opacity: 0 }}
    >
      <div className="flex items-start justify-between mb-3">
        <span className="text-[10px] font-bold text-dim uppercase tracking-wider">{label}</span>
        <div className={`p-1.5 rounded-lg bg-muted`}>
          <Icon size={14} className={color} />
        </div>
      </div>
      <div className={`stat-number text-2xl ${color}`}>{value ?? '—'}</div>
    </div>
  )
}

/* ── Agent pipeline diagram ────────────────── */
function PipelineDiagram() {
  const nodes = [
    { label: 'Supervisor',   color: 'text-gold   border-gold/20   bg-gold/5',   icon: Cpu },
    { label: 'Data Analyst', color: 'text-indigo border-indigo/20 bg-indigo/5', icon: Database },
    { label: 'Insight',      color: 'text-sage   border-sage/20   bg-sage/5',   icon: Activity },
    { label: 'Report',       color: 'text-text   border-border    bg-muted/30',  icon: BarChart2 },
  ]
  return (
    <div className="px-3 py-2">
      <p className="text-[10px] font-bold text-dim uppercase tracking-wider mb-4">Intelligence Pipeline</p>
      <div className="space-y-1.5">
        {nodes.map((n, i) => {
          const Icon = n.icon
          return (
            <React.Fragment key={n.label}>
              <div className={`flex items-center gap-3 px-3 py-2.5 rounded-xl border ${n.color} transition-colors`}>
                <Icon size={12} />
                <span className="text-xs font-semibold">{n.label}</span>
              </div>
              {i < nodes.length - 1 && (
                <div className="flex justify-center my-0.5">
                  <div className="w-px h-3 bg-border" />
                </div>
              )}
            </React.Fragment>
          )
        })}
      </div>
    </div>
  )
}

/* ── KPI legend ───────────────────────────── */
function KpiList({ kpis = [] }) {
  if (!kpis.length) return null
  const display = kpis.filter(k => !k.startsWith('norm_')).slice(0, 8)
  return (
    <div className="px-3 py-2">
      <p className="text-[10px] font-bold text-dim uppercase tracking-wider mb-3">Available Metrics</p>
      <div className="flex flex-wrap gap-2">
        {display.map(k => (
          <span key={k} className="text-[10px] font-medium text-dim bg-muted border border-border/50 rounded-lg px-2.5 py-1">
            {k}
          </span>
        ))}
      </div>
    </div>
  )
}

/* ── Sidebar section divider ──────────────── */
function Divider() {
  return <div className="h-px bg-border/40 mx-4 my-2" />
}

/* ── Main Dashboard ───────────────────────── */
export default function Dashboard() {
  const [health, setHealth]         = useState(null)
  const [dataset, setDataset]       = useState(null)
  const [suggestions, setSuggestions] = useState([])
  const [status, setStatus]         = useState('loading')

  useEffect(() => {
    Promise.all([
      getHealth().catch(() => null),
      getDatasetInfo().catch(() => null),
      getSuggestions().catch(() => ({ suggestions: [] })),
    ]).then(([h, d, s]) => {
      setHealth(h)
      setDataset(d)
      setSuggestions(s?.suggestions || [])
      setStatus(h ? 'ok' : 'error')
    })
  }, [])

  return (
    <div className="flex h-screen overflow-hidden warm-bg font-body">

      {/* ══ Sidebar ══════════════════════════════ */}
      <aside className="w-60 flex-shrink-0 bg-white/50 backdrop-blur-md border-r border-border flex flex-col overflow-y-auto">

        {/* Logo */}
        <div className="px-5 py-6 flex-shrink-0">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-9 h-9 rounded-xl bg-accent flex items-center justify-center text-white shadow-accent">
              <Zap size={18} fill="currentColor" />
            </div>
            <div>
              <div className="font-display font-bold text-base text-text leading-none tracking-tight">Campaign AI</div>
              <div className="text-[10px] font-bold text-dim/60 uppercase tracking-widest mt-1">Intelligence Hub</div>
            </div>
          </div>
          <div className="mt-4">
            <StatusBadge status={status} />
          </div>
        </div>

        {/* Stats */}
        <div className="px-4 py-2 grid grid-cols-2 gap-3">
          <StatCard
            label="Campaigns"
            value={health?.campaigns_count ?? dataset?.campaigns?.length}
            icon={Layers}
            color="text-indigo"
            delay={100}
          />
          <StatCard
            label="Segments"
            value={health?.segments_available?.length ?? dataset?.segments?.length}
            icon={Globe}
            color="text-accent"
            delay={200}
          />
        </div>

        {/* Pipeline */}
        <div className="mt-4">
          <Divider />
          <PipelineDiagram />
        </div>

        {/* KPIs */}
        {dataset?.kpi_columns?.length > 0 && (
          <div className="mt-2">
            <Divider />
            <KpiList kpis={dataset.kpi_columns} />
          </div>
        )}

        {/* Segments */}
        {health?.segments_available?.length > 0 && (
          <div className="px-4 py-4 mt-auto border-t border-border/40">
            <p className="text-[10px] font-bold text-dim uppercase tracking-wider mb-3">Target Groups</p>
            <div className="flex flex-wrap gap-1.5">
              {health.segments_available.map(s => (
                <span key={s} className="text-[10px] font-medium text-dim bg-muted border border-border/50 rounded-lg px-2 py-0.5">
                  {s}
                </span>
              ))}
            </div>
          </div>
        )}
      </aside>

      {/* ══ Main content ═════════════════════════ */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        <div className="absolute inset-0 bg-soft-glow pointer-events-none" />
        
        {/* Header */}
        <header className="flex-shrink-0 h-16 border-b border-border/40 bg-white/40 backdrop-blur-md flex items-center justify-between px-6 z-10">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-2xl bg-indigo/10 flex items-center justify-center">
              <BarChart2 size={18} className="text-indigo" />
            </div>
            <div>
              <h1 className="font-display font-bold text-base text-text leading-none">
                Campaign Intelligence
              </h1>
              <p className="text-[11px] text-dim font-medium leading-none mt-1.5 flex items-center gap-1.5">
                <span className="w-1 h-1 rounded-full bg-indigo" />
                Multi-Agent Analysis Engine
              </p>
            </div>
          </div>

          {/* Right: model badge */}
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2.5 px-4 py-2 bg-white/50 border border-border/60 rounded-full shadow-soft">
              <div className="w-2 h-2 rounded-full bg-sage animate-pulse" />
              <span className="text-xs font-semibold text-text/70 tracking-tight">Intelligence Pipeline Active</span>
            </div>
          </div>
        </header>

        {/* Chat area */}
        <div className="flex-1 min-h-0 relative flex flex-col">
          <Chat suggestions={suggestions} />
        </div>
      </div>
    </div>
  )
}