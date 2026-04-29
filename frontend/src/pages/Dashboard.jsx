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
    <div className="flex items-center gap-1.5 text-dim text-xs font-mono">
      <Loader2 size={11} className="animate-spin" />
      connecting
    </div>
  )
  if (status === 'ok') return (
    <div className="flex items-center gap-1.5 text-sage text-xs font-mono">
      <CheckCircle2 size={11} />
      online
    </div>
  )
  return (
    <div className="flex items-center gap-1.5 text-rose text-xs font-mono">
      <XCircle size={11} />
      offline
    </div>
  )
}

/* ── Stat card ─────────────────────────────── */
function StatCard({ label, value, icon: Icon, color = 'text-accent', delay = 0 }) {
  return (
    <div
      className="bg-card border border-border rounded-xl p-3.5 animate-fade-up"
      style={{ animationDelay: `${delay}ms`, opacity: 0 }}
    >
      <div className="flex items-start justify-between mb-2">
        <span className="text-[10px] font-mono text-dim uppercase tracking-widest">{label}</span>
        <Icon size={13} className={color} />
      </div>
      <div className={`stat-number text-xl ${color}`}>{value ?? '—'}</div>
    </div>
  )
}

/* ── Agent pipeline diagram ────────────────── */
function PipelineDiagram() {
  const nodes = [
    { label: 'Supervisor',   color: 'text-gold   border-gold/30   bg-gold/5',   icon: Cpu },
    { label: 'Data Analyst', color: 'text-accent border-accent/30 bg-accent/5', icon: Database },
    { label: 'Insight',      color: 'text-sage   border-sage/30   bg-sage/5',   icon: Activity },
    { label: 'Report',       color: 'text-text   border-border    bg-card',      icon: BarChart2 },
  ]
  return (
    <div className="px-3 py-2">
      <p className="text-[10px] font-mono text-dim uppercase tracking-widest mb-3">Agent pipeline</p>
      <div className="space-y-1">
        {nodes.map((n, i) => {
          const Icon = n.icon
          return (
            <React.Fragment key={n.label}>
              <div className={`flex items-center gap-2.5 px-3 py-2 rounded-lg border ${n.color}`}>
                <Icon size={11} />
                <span className="text-xs font-mono">{n.label}</span>
              </div>
              {i < nodes.length - 1 && (
                <div className="flex justify-center">
                  <ChevronRight size={10} className="text-dim rotate-90" />
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
      <p className="text-[10px] font-mono text-dim uppercase tracking-widest mb-2">Available KPIs</p>
      <div className="flex flex-wrap gap-1.5">
        {display.map(k => (
          <span key={k} className="text-[10px] font-mono text-dim bg-muted/30 border border-border/60 rounded px-2 py-0.5">
            {k}
          </span>
        ))}
      </div>
    </div>
  )
}

/* ── Sidebar section divider ──────────────── */
function Divider() {
  return <div className="h-px bg-border/60 mx-3" />
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
    <div className="flex h-screen overflow-hidden bg-ink grid-bg font-body">

      {/* ══ Sidebar ══════════════════════════════ */}
      <aside className="w-56 flex-shrink-0 bg-panel border-r border-border flex flex-col overflow-y-auto">

        {/* Logo */}
        <div className="px-4 py-5 border-b border-border flex-shrink-0">
          <div className="flex items-center gap-2.5 mb-0.5">
            <div className="w-7 h-7 rounded-lg bg-accent/15 border border-accent/30 flex items-center justify-center">
              <Zap size={13} className="text-accent" />
            </div>
            <div>
              <div className="font-display font-bold text-sm text-text leading-none">Campaign AI</div>
              <div className="text-[10px] font-mono text-dim leading-none mt-0.5">Intelligence Agent</div>
            </div>
          </div>
        </div>

        {/* Status */}
        <div className="px-4 py-3 border-b border-border flex-shrink-0">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-dim uppercase tracking-widest">API Status</span>
            <StatusBadge status={status} />
          </div>
        </div>

        {/* Stats */}
        <div className="p-3 grid grid-cols-2 gap-2 border-b border-border">
          <StatCard
            label="Campaigns"
            value={health?.campaigns_count ?? dataset?.campaigns?.length}
            icon={Layers}
            color="text-accent"
            delay={100}
          />
          <StatCard
            label="Segments"
            value={health?.segments_available?.length ?? dataset?.segments?.length}
            icon={Globe}
            color="text-gold"
            delay={200}
          />
        </div>

        {/* Pipeline */}
        <Divider />
        <PipelineDiagram />

        {/* KPIs */}
        {dataset?.kpi_columns?.length > 0 && (
          <>
            <Divider />
            <KpiList kpis={dataset.kpi_columns} />
          </>
        )}

        {/* Segments */}
        {health?.segments_available?.length > 0 && (
          <div className="px-3 py-2 mt-auto border-t border-border">
            <p className="text-[10px] font-mono text-dim uppercase tracking-widest mb-2">Target Groups</p>
            <div className="flex flex-wrap gap-1">
              {health.segments_available.map(s => (
                <span key={s} className="text-[10px] font-mono text-dim/80 bg-muted/20 rounded px-1.5 py-0.5 border border-border/40">
                  {s}
                </span>
              ))}
            </div>
          </div>
        )}
      </aside>

      {/* ══ Main content ═════════════════════════ */}
      <div className="flex-1 flex flex-col min-w-0">

        {/* Header */}
        <header className="flex-shrink-0 h-14 border-b border-border bg-panel/60 backdrop-blur-md flex items-center justify-between px-5">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-8 h-8 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center overflow-hidden">
                <BarChart2 size={15} className="text-accent" />
                <div className="scan-line" />
              </div>
            </div>
            <div>
              <h1 className="font-display font-bold text-sm text-text leading-none">
                Campaign Intelligence
              </h1>
              <p className="text-[11px] text-dim font-mono leading-none mt-0.5">
                Powered by LangGraph · GPT-4o
              </p>
            </div>
          </div>

          {/* Right: model badge */}
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-card border border-border rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-sage animate-pulse-slow" />
              <span className="text-[11px] font-mono text-dim">4-Agent Pipeline</span>
            </div>
          </div>
        </header>

        {/* Chat area */}
        <div className="flex-1 overflow-hidden">
          <Chat suggestions={suggestions} />
        </div>
      </div>
    </div>
  )
}