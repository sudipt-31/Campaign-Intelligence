import React from 'react'
import {
  BarChart, Bar,
  LineChart, Line,
  PieChart, Pie, Cell,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'

/* ── Palette ─────────────────────────────────── */
const COLORS = [
  '#F59E0B', // Amber
  '#6366F1', // Indigo
  '#10B981', // Sage
  '#F43F5E', // Rose
  '#8B5CF6', // Violet
  '#EC4899', // Pink
  '#06B6D4', // Cyan
  '#F97316'  // Orange
]

/* ── Custom tooltip ──────────────────────────── */
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-border/60 rounded-xl px-4 py-3 shadow-card backdrop-blur-md bg-white/90">
      <p className="text-dim text-[10px] font-bold uppercase tracking-wider mb-2">{label}</p>
      <div className="space-y-1.5">
        {payload.map((p, i) => (
          <div key={i} className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full" style={{ background: p.fill || p.color }} />
              <span className="text-text/70 text-xs font-medium">{p.name}</span>
            </div>
            <span className="text-text text-sm font-display font-bold">{p.value?.toLocaleString?.() ?? p.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Custom pie label ──────────────────────────── */
const renderPieLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, name, value }) => {
  const RADIAN = Math.PI / 180
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5
  const x = cx + radius * Math.cos(-midAngle * RADIAN)
  const y = cy + radius * Math.sin(-midAngle * RADIAN)
  if (value < 5) return null
  return (
    <text x={x} y={y} fill="#fff" textAnchor="middle" dominantBaseline="central" fontSize={10} fontWeight={700} fontFamily="Plus Jakarta Sans">
      {value?.toFixed?.(0)}%
    </text>
  )
}

/* ── Data Table ──────────────────────────────── */
function DataTable({ columns = [], rows = [] }) {
  if (!columns.length) return null
  return (
    <div className="overflow-x-auto rounded-2xl border border-border/60 mt-2 shadow-soft bg-white/50">
      <table className="w-full text-xs font-body">
        <thead>
          <tr className="border-b border-border/40 bg-muted/30">
            {columns.map((col, i) => (
              <th
                key={i}
                className="px-4 py-3 text-left text-dim uppercase tracking-wider whitespace-nowrap font-bold text-[10px]"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr
              key={ri}
              className={`border-b border-border/20 transition-colors hover:bg-accent/5 ${ri % 2 === 0 ? 'bg-transparent' : 'bg-muted/10'}`}
            >
              {row.map((cell, ci) => (
                <td key={ci} className="px-4 py-3 text-text/80 whitespace-nowrap font-medium">
                  {typeof cell === 'number' ? cell.toLocaleString() : cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ── Main Chart component ──────────────────────── */
export default function Chart({ data = [], type = 'bar', title, tableData = null }) {
  const hasTable = type === 'table' && tableData?.columns?.length > 0

  const sharedProps = {
    margin: { top: 12, right: 12, left: -12, bottom: 0 },
  }

  const axisStyle = {
    tick:     { fill: '#7C726A', fontSize: 10, fontWeight: 600, fontFamily: 'Plus Jakarta Sans' },
    axisLine: { stroke: '#EDE9E6' },
    tickLine: false,
  }

  const gridStyle = {
    strokeDasharray: '6 6',
    stroke: '#EDE9E6',
    vertical: false,
  }

  // Normalize: ensure all values are numbers
  const clean = (data || []).map(d => ({ ...d, value: parseFloat(d.value) || 0 }))

  const titleBlock = title && (
    <h3 className="text-xs font-mono text-dim uppercase tracking-widest mb-4 flex items-center gap-2">
      <span className="w-1 h-4 bg-accent rounded-full inline-block" />
      {title}
    </h3>
  )

  // ── Table mode ────────────────────────────────
  if (hasTable) {
    return (
      <div className="w-full animate-fade-in">
        {titleBlock}
        <DataTable columns={tableData.columns} rows={tableData.rows} />
      </div>
    )
  }

  if (!clean?.length) return null

  return (
    <div className="w-full animate-fade-in">
      {titleBlock}

      <ResponsiveContainer width="100%" height={260}>
        {type === 'line' ? (
          <LineChart data={clean} {...sharedProps}>
            <CartesianGrid {...gridStyle} />
            <XAxis dataKey="name" {...axisStyle} />
            <YAxis {...axisStyle} />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#00D4FF"
              strokeWidth={2.5}
              dot={{ fill: '#00D4FF', r: 4, strokeWidth: 0 }}
              activeDot={{ r: 6, fill: '#fff', stroke: '#00D4FF', strokeWidth: 2 }}
            />
          </LineChart>

        ) : type === 'pie' ? (
          <PieChart>
            <Pie
              data={clean}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={100}
              innerRadius={44}
              paddingAngle={3}
              labelLine={false}
              label={renderPieLabel}
            >
              {clean.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} stroke="transparent" />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: '11px', fontFamily: 'JetBrains Mono', color: '#607080' }}
            />
          </PieChart>

        ) : type === 'radar' ? (
          <RadarChart cx="50%" cy="50%" outerRadius={100} data={clean}>
            <PolarGrid stroke="#1E2A38" />
            <PolarAngleAxis
              dataKey="name"
              tick={{ fill: '#607080', fontSize: 11, fontFamily: 'JetBrains Mono' }}
            />
            <PolarRadiusAxis tick={{ fill: '#607080', fontSize: 9 }} />
            <Radar
              name="value"
              dataKey="value"
              stroke="#00D4FF"
              fill="#00D4FF"
              fillOpacity={0.15}
              strokeWidth={2}
            />
            <Tooltip content={<CustomTooltip />} />
          </RadarChart>

        ) : (
          /* Default: bar */
          <BarChart data={clean} {...sharedProps}>
            <CartesianGrid {...gridStyle} />
            <XAxis dataKey="name" {...axisStyle} />
            <YAxis {...axisStyle} />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0,212,255,0.04)' }} />
            <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={52}>
              {clean.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}

/* ── Named export for DataTable (used by Chat) ── */
export { DataTable }