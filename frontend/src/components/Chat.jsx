import React, { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Send, Loader2, Bot, User, ChevronRight,
  TrendingUp, AlertCircle, Lightbulb, Activity,
  BarChart2, Database, Brain, FileText,
  Sparkles, RefreshCw, MessageSquare, History,
} from 'lucide-react'
import Chart, { DataTable } from './Chart.jsx'
import { queryAgent } from '../api.js'

/* ── Agent metadata ───────────────────────────── */
const AGENT_META = {
  supervisor:    { label: 'Supervisor',    color: 'text-gold   bg-gold/10   border-gold/20',   icon: Brain },
  data_analyst:  { label: 'Data Analyst',  color: 'text-indigo bg-indigo/10 border-indigo/20', icon: Database },
  insight_agent: { label: 'Insight',       color: 'text-sage   bg-sage/10   border-sage/20',   icon: TrendingUp },
  report_writer: { label: 'Report Writer', color: 'text-text   bg-muted     border-border',     icon: FileText },
}

/* ── Thinking animation ───────────────────────── */
function ThinkingDots() {
  return (
    <div className="flex items-center gap-1.5 py-1">
      {[0, 1, 2].map(i => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-accent/40"
          style={{ animation: `bounceSoft 1.2s ease-in-out ${i * 0.2}s infinite` }}
        />
      ))}
    </div>
  )
}

/* ── Agent trace badges ───────────────────────── */
function AgentTrace({ agents = [] }) {
  if (!agents.length) return null
  return (
    <div className="flex flex-wrap items-center gap-2 mt-4 pt-4 border-t border-border/40">
      <span className="text-[10px] font-bold text-dim/60 uppercase tracking-widest">pipeline:</span>
      {agents.map((a, i) => {
        const meta = AGENT_META[a] || { label: a, color: 'text-dim bg-muted border-border/50', icon: Activity }
        const Icon = meta.icon
        return (
          <React.Fragment key={a}>
            <span className={`agent-pill border ${meta.color} shadow-sm`}>
              <Icon size={11} />
              {meta.label}
            </span>
            {i < agents.length - 1 && <ChevronRight size={10} className="text-dim/40" />}
          </React.Fragment>
        )
      })}
    </div>
  )
}

/* ── Recommendation card ───────────────────────── */
function RecommendationCard({ rec, index, onAsk }) {
  return (
    <button
      onClick={() => onAsk(rec)}
      className="w-full text-left flex gap-3.5 p-3.5 rounded-2xl bg-white border border-border/60 shadow-soft hover:shadow-card hover:border-accent/40 hover:bg-accent/[0.02] transition-all group"
      style={{ animationDelay: `${index * 80}ms` }}
      title="Click to ask this question"
    >
      <span className="flex-shrink-0 w-6 h-6 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center text-accent text-xs font-bold group-hover:bg-accent group-hover:text-white group-hover:border-accent transition-all">
        {index + 1}
      </span>
      <p className="text-text/80 text-[13px] font-medium leading-relaxed flex-1">{rec}</p>
      <span className="flex-shrink-0 text-accent/30 group-hover:text-accent transition-colors self-center text-lg leading-none">→</span>
    </button>
  )
}

/* ── Rich-text markdown renderer ─────────────── */
const MD_COMPONENTS = {
  h2: ({ children }) => (
    <h2 style={{ fontSize:'16px', fontWeight:700, color:'#332D2D', marginTop:0, marginBottom:'12px', paddingBottom:'8px', borderBottom:'1px solid #EDE9E6', fontFamily:'Outfit,sans-serif', lineHeight:1.3 }}>
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 style={{ fontSize:'14px', fontWeight:600, color:'#6366F1', marginTop:'16px', marginBottom:'8px', fontFamily:'Outfit,sans-serif' }}>
      {children}
    </h3>
  ),
  p: ({ children }) => (
    <p style={{ fontSize:'14px', color:'#4B443F', lineHeight:1.6, marginBottom:'12px', marginTop:0 }}>{children}</p>
  ),
  strong: ({ children }) => (
    <strong style={{ color:'#332D2D', fontWeight:700 }}>{children}</strong>
  ),
  em: ({ children }) => (
    <em style={{ color:'#D97706', fontStyle:'italic', fontWeight:500 }}>{children}</em>
  ),
  ul: ({ children }) => (
    <ul style={{ margin:'0 0 12px 0', padding:0, listStyle:'none' }}>{children}</ul>
  ),
  ol: ({ children }) => (
    <ol style={{ margin:'0 0 12px 0', paddingLeft:'20px' }}>{children}</ol>
  ),
  li: ({ children }) => (
    <li style={{ display:'flex', gap:'10px', fontSize:'14px', color:'#4B443F', lineHeight:1.6, marginBottom:'6px' }}>
      <span style={{ color:'#F59E0B', marginTop:'4px', flexShrink:0, fontSize:'16px', lineHeight:1 }}>•</span>
      <span>{children}</span>
    </li>
  ),
  /* Markdown tables (GFM) */
  table: ({ children }) => (
    <div style={{ overflowX:'auto', borderRadius:'12px', border:'1px solid #EDE9E6', margin:'16px 0', boxShadow:'0 4px 12px rgba(45, 40, 37, 0.04)' }}>
      <table style={{ width:'100%', fontSize:'12.5px', borderCollapse:'collapse' }}>{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead style={{ background:'#FDFCFB', borderBottom:'1px solid #EDE9E6' }}>{children}</thead>
  ),
  tbody: ({ children }) => <tbody>{children}</tbody>,
  tr: ({ children }) => (
    <tr style={{ borderBottom:'1px solid rgba(237,233,230,0.6)' }}>
      {children}
    </tr>
  ),
  th: ({ children }) => (
    <th style={{ padding:'10px 14px', textAlign:'left', color:'#7C726A', textTransform:'uppercase', letterSpacing:'0.05em', fontWeight:700, whiteSpace:'nowrap', fontSize:'10px' }}>
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td style={{ padding:'10px 14px', color:'#4B443F', whiteSpace:'nowrap' }}>{children}</td>
  ),
  code: ({ inline, children }) =>
    inline ? (
      <code style={{ background:'#F3F1EF', color:'#6366F1', fontSize:'12px', padding:'2px 6px', borderRadius:'6px', fontFamily:'JetBrains Mono,monospace', fontWeight:500 }}>{children}</code>
    ) : (
      <pre style={{ background:'#FFFFFF', border:'1px solid #EDE9E6', borderRadius:'12px', padding:'14px', overflowX:'auto', margin:'12px 0', boxShadow:'inset 0 2px 4px 0 rgba(45, 40, 37, 0.02)' }}>
        <code style={{ color:'#4B443F', fontSize:'12.5px', fontFamily:'JetBrains Mono,monospace', lineHeight:1.5 }}>{children}</code>
      </pre>
    ),
  blockquote: ({ children }) => (
    <blockquote style={{ borderLeft:'4px solid #F59E0B', paddingLeft:'16px', margin:'16px 0', color:'#7C726A', fontStyle:'italic', fontSize:'14px', background:'rgba(245, 158, 11, 0.03)', padding:'12px 16px', borderRadius:'0 12px 12px 0' }}>
      {children}
    </blockquote>
  ),
  hr: () => <hr style={{ border:'none', borderTop:'1px solid #EDE9E6', margin:'16px 0' }} />,
}

/* ── RichTextBlock ─────────────────────────────── */
function RichTextBlock({ markdown }) {
  if (!markdown) return null
  return (
    <div style={{ lineHeight: 1.6 }}>
      <ReactMarkdown components={MD_COMPONENTS} remarkPlugins={[remarkGfm]}>
        {markdown}
      </ReactMarkdown>
    </div>
  )
}

/* ── Single message bubble ────────────────────── */
function MessageBubble({ msg, onAsk }) {
  const isUser = msg.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end msg-enter">
        <div className="max-w-[75%] flex items-start gap-3">
          <div className="bg-indigo/10 border border-indigo/20 rounded-2xl rounded-tr-sm px-4 py-3 shadow-soft">
            <p className="text-text text-[14px] font-medium leading-relaxed">{msg.content}</p>
          </div>
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-white border border-border shadow-soft flex items-center justify-center mt-1">
            <User size={14} className="text-indigo" />
          </div>
        </div>
      </div>
    )
  }

  if (msg.thinking) {
    return (
      <div className="flex items-start gap-4 msg-enter">
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center shadow-soft">
          <Bot size={15} className="text-accent" />
        </div>
        <div className="bg-white border border-border/60 rounded-2xl rounded-tl-sm px-5 py-4 shadow-card">
          <div className="flex items-center gap-2.5 text-dim text-[11px] font-bold uppercase tracking-wider mb-2">
            <Loader2 size={12} className="animate-spin text-accent" />
            Processing Analysis
          </div>
          <ThinkingDots />
        </div>
      </div>
    )
  }

  const hasRichText = !!msg.richText
  const hasChart    = msg.chart?.length > 0
  const hasTable    = msg.chartType === 'table' && msg.tableData?.columns?.length > 0

  return (
    <div className="flex items-start gap-4 msg-enter">
      {/* Bot avatar */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center mt-1 shadow-soft">
        <Bot size={15} className="text-accent" />
      </div>

      {/* Bubble */}
      <div className="flex-1 min-w-0 space-y-4">
        {/* Main response card */}
        <div className="bg-white border border-border/60 rounded-2xl rounded-tl-sm px-6 py-5 shadow-card">

          {/* Rich text — takes priority if available */}
          {hasRichText ? (
            <RichTextBlock markdown={msg.richText} />
          ) : (
            <p className="text-text text-[14px] leading-relaxed font-medium">{msg.content}</p>
          )}

          {/* Data table (chart_type === 'table') */}
          {hasTable && (
            <div className="mt-6 pt-5 border-t border-border/40">
              <p className="text-[10px] font-bold text-dim uppercase tracking-wider mb-3 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                {msg.chartTitle || 'Data Analysis'}
              </p>
              <DataTable columns={msg.tableData.columns} rows={msg.tableData.rows} />
            </div>
          )}

          {/* Chart */}
          {!hasTable && hasChart && (
            <div className="mt-6 pt-5 border-t border-border/40">
              <Chart
                data={msg.chart}
                type={msg.chartType}
                title={msg.chartTitle}
                tableData={msg.tableData}
              />
            </div>
          )}

          {/* Agent trace */}
          {msg.agentTrace?.length > 0 && (
            <AgentTrace agents={msg.agentTrace} />
          )}
        </div>

        {/* Recommendations */}
        {msg.recommendations?.length > 0 && (
          <div className="bg-white/40 border border-border/40 rounded-2xl px-6 py-5">
            <div className="flex items-center gap-2.5 mb-4">
              <div className="p-1.5 rounded-lg bg-gold/10">
                <Lightbulb size={14} className="text-gold" />
              </div>
              <span className="text-[11px] font-bold text-gold uppercase tracking-wider">Suggested Insights</span>
            </div>
            <div className="space-y-3">
              {msg.recommendations.map((rec, i) => (
                <RecommendationCard key={i} rec={rec} index={i} onAsk={onAsk} />
              ))}
            </div>
          </div>
        )}

        {/* Error */}
        {msg.error && (
          <div className="flex items-start gap-3 px-5 py-4 bg-rose/5 border border-rose/20 rounded-2xl">
            <AlertCircle size={15} className="text-rose mt-0.5 flex-shrink-0" />
            <p className="text-rose/80 text-[13px] font-medium leading-relaxed">{msg.error}</p>
          </div>
        )}
      </div>
    </div>
  )
}

/* ── Suggestion chip ──────────────────────────── */
function SuggestionChip({ text, onClick }) {
  return (
    <button
      onClick={() => onClick(text)}
      className="text-left px-4 py-3 rounded-2xl border border-border bg-white shadow-soft hover:shadow-card hover:border-accent/40 hover:bg-accent/[0.02] transition-all text-[13px] font-medium text-text/70 hover:text-text group flex items-center gap-2"
    >
      <Sparkles size={13} className="text-accent/40 group-hover:text-accent transition-colors" />
      {text}
    </button>
  )
}

/* ── Chat history indicator ───────────────────── */
function HistoryBadge({ count }) {
  if (count <= 1) return null
  return (
    <div className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-border/60 rounded-full shadow-soft">
      <History size={11} className="text-indigo/60" />
      <span className="text-[10px] font-bold text-text/50 uppercase tracking-wider">{count} steps in memory</span>
    </div>
  )
}

/* ── Main Chat ─────────────────────────────────── */
export default function Chat({ suggestions = [] }) {
  const [messages, setMessages] = useState([])
  const [input, setInput]       = useState('')
  const [loading, setLoading]   = useState(false)
  const chatEndRef              = useRef(null)

  const scrollToBottom = useCallback(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => { scrollToBottom() }, [messages, loading, scrollToBottom])

  const onSend = async (text = input) => {
    if (!text.trim() || loading) return
    
    const userMsg = { role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await queryAgent(text)
      setMessages(prev => [...prev, { 
        role:            'assistant', 
        content:         res.content || res.summary || 'Analysis complete.',
        richText:        res.rich_text, 
        agentTrace:      res.agent_trace, 
        chart:           res.chart, 
        chartType:       res.chart_type, 
        chartTitle:      res.chart_title, 
        tableData:       res.table_data, 
        recommendations: res.recommendations 
      }])
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error.', error: err.message }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-transparent relative">
      
      {/* Scrollable messages */}
      <div className="flex-1 overflow-y-auto px-6 py-8 space-y-8 custom-scrollbar scroll-smooth">
        {messages.length === 0 && !loading && (
          <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto text-center space-y-6 animate-fade-in">
            <div className="w-16 h-16 rounded-3xl bg-accent/10 flex items-center justify-center text-accent mb-2">
              <MessageSquare size={32} />
            </div>
            <div>
              <h2 className="text-2xl font-display font-bold text-text mb-3 tracking-tight">How can I help you today?</h2>
              <p className="text-text/60 text-base font-medium max-w-md mx-auto">
                Ask me about campaign performance, customer segments, or any data insights you need.
              </p>
            </div>
            
            <div className="w-full pt-4">
              <p className="text-[10px] font-bold text-dim/50 uppercase tracking-[0.2em] mb-6">Popular starting points</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {suggestions.slice(0, 4).map((s, i) => (
                  <SuggestionChip key={i} text={s} onClick={onSend} />
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <MessageBubble key={i} msg={m} onAsk={onSend} />
        ))}
        
        {loading && <MessageBubble msg={{ role: 'assistant', thinking: true }} />}
        <div ref={chatEndRef} />
      </div>

      {/* Input area */}
      <div className="flex-shrink-0 p-6 pt-0">
        <div className="max-w-4xl mx-auto relative">
          
          {/* History badge */}
          <div className="absolute -top-12 left-0 right-0 flex justify-center pointer-events-none">
            <HistoryBadge count={messages.length} />
          </div>

          <div className="bg-white border border-border shadow-card rounded-[24px] p-2 flex items-center gap-2 focus-within:border-accent/40 focus-within:shadow-accent/5 transition-all">
            <div className="flex-shrink-0 pl-3 text-dim/40">
              <RefreshCw size={18} className={loading ? 'animate-spin text-accent' : ''} />
            </div>
            <input
              className="flex-1 bg-transparent border-none outline-none text-[15px] font-medium text-text placeholder:text-text/30 py-3 px-1"
              placeholder="Ask anything about your campaigns..."
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && onSend()}
              disabled={loading}
            />
            <button
              onClick={() => onSend()}
              disabled={loading || !input.trim()}
              className="flex-shrink-0 w-11 h-11 rounded-2xl bg-accent text-white flex items-center justify-center shadow-accent hover:bg-gold transition-all disabled:opacity-30 disabled:shadow-none"
            >
              <Send size={18} fill="currentColor" />
            </button>
          </div>
          
          <p className="text-center mt-3 text-[10px] font-bold text-dim/40 uppercase tracking-widest">
            AI-Powered Campaign Intelligence Hub
          </p>
        </div>
      </div>
    </div>
  )
}