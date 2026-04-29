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
  data_analyst:  { label: 'Data Analyst',  color: 'text-accent bg-accent/10 border-accent/20', icon: Database },
  insight_agent: { label: 'Insight',       color: 'text-sage   bg-sage/10   border-sage/20',   icon: TrendingUp },
  report_writer: { label: 'Report Writer', color: 'text-text   bg-muted/30  border-border',     icon: FileText },
}

/* ── Thinking animation ───────────────────────── */
function ThinkingDots() {
  return (
    <div className="flex items-center gap-1.5 py-1">
      {[0, 1, 2].map(i => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-accent/60"
          style={{ animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite` }}
        />
      ))}
    </div>
  )
}

/* ── Agent trace badges ───────────────────────── */
function AgentTrace({ agents = [] }) {
  if (!agents.length) return null
  return (
    <div className="flex flex-wrap items-center gap-1.5 mt-3 pt-3 border-t border-border/50">
      <span className="text-xs text-dim font-mono">pipeline:</span>
      {agents.map((a, i) => {
        const meta = AGENT_META[a] || { label: a, color: 'text-dim bg-muted/20 border-border', icon: Activity }
        const Icon = meta.icon
        return (
          <React.Fragment key={a}>
            <span className={`agent-pill border ${meta.color}`}>
              <Icon size={10} />
              {meta.label}
            </span>
            {i < agents.length - 1 && <ChevronRight size={10} className="text-dim" />}
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
      className="w-full text-left flex gap-3 p-3 rounded-lg bg-ink/50 border border-border/50 hover:border-accent/40 hover:bg-accent/5 transition-all group"
      style={{ animationDelay: `${index * 80}ms` }}
      title="Click to ask this question"
    >
      <span className="flex-shrink-0 w-5 h-5 rounded-full bg-accent/10 border border-accent/30 flex items-center justify-center text-accent text-[10px] font-mono font-bold mt-0.5 group-hover:bg-accent group-hover:text-white group-hover:border-accent transition-all">
        {index + 1}
      </span>
      <p className="text-text/80 text-sm leading-relaxed flex-1">{rec}</p>
      <span className="flex-shrink-0 text-accent/30 group-hover:text-accent transition-colors self-center text-base leading-none">→</span>
    </button>
  )
}

/* ── Rich-text markdown renderer ─────────────── */
const MD_COMPONENTS = {
  h2: ({ children }) => (
    <h2 style={{ fontSize:'15px', fontWeight:700, color:'#0F172A', marginTop:0, marginBottom:'8px', paddingBottom:'6px', borderBottom:'1px solid #E2E8F0', fontFamily:'Syne,sans-serif', lineHeight:1.3 }}>
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 style={{ fontSize:'13px', fontWeight:600, color:'#1E3A8A', marginTop:'14px', marginBottom:'6px', fontFamily:'Syne,sans-serif' }}>
      {children}
    </h3>
  ),
  p: ({ children }) => (
    <p style={{ fontSize:'13.5px', color:'#1e293b', lineHeight:1.65, marginBottom:'8px', marginTop:0 }}>{children}</p>
  ),
  strong: ({ children }) => (
    <strong style={{ color:'#0F172A', fontWeight:700 }}>{children}</strong>
  ),
  em: ({ children }) => (
    <em style={{ color:'#D97706', fontStyle:'italic' }}>{children}</em>
  ),
  ul: ({ children }) => (
    <ul style={{ margin:'0 0 8px 0', padding:0, listStyle:'none' }}>{children}</ul>
  ),
  ol: ({ children }) => (
    <ol style={{ margin:'0 0 8px 0', paddingLeft:'18px' }}>{children}</ol>
  ),
  li: ({ children }) => (
    <li style={{ display:'flex', gap:'8px', fontSize:'13.5px', color:'#334155', lineHeight:1.6, marginBottom:'3px' }}>
      <span style={{ color:'#1E3A8A', marginTop:'2px', flexShrink:0, fontWeight:700 }}>›</span>
      <span>{children}</span>
    </li>
  ),
  /* Markdown tables (GFM) */
  table: ({ children }) => (
    <div style={{ overflowX:'auto', borderRadius:'10px', border:'1px solid #E2E8F0', margin:'10px 0' }}>
      <table style={{ width:'100%', fontSize:'12px', fontFamily:'JetBrains Mono,monospace', borderCollapse:'collapse' }}>{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead style={{ background:'#F1F5F9', borderBottom:'1px solid #E2E8F0' }}>{children}</thead>
  ),
  tbody: ({ children }) => <tbody>{children}</tbody>,
  tr: ({ children }) => (
    <tr style={{ borderBottom:'1px solid rgba(226,232,240,0.7)' }}>
      {children}
    </tr>
  ),
  th: ({ children }) => (
    <th style={{ padding:'8px 12px', textAlign:'left', color:'#475569', textTransform:'uppercase', letterSpacing:'0.07em', fontWeight:600, whiteSpace:'nowrap', fontSize:'11px' }}>
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td style={{ padding:'7px 12px', color:'#334155', whiteSpace:'nowrap' }}>{children}</td>
  ),
  code: ({ inline, children }) =>
    inline ? (
      <code style={{ background:'#F1F5F9', color:'#1E3A8A', fontSize:'11px', padding:'1px 5px', borderRadius:'4px', fontFamily:'JetBrains Mono,monospace' }}>{children}</code>
    ) : (
      <pre style={{ background:'#F8FAFC', border:'1px solid #E2E8F0', borderRadius:'8px', padding:'10px', overflowX:'auto', margin:'8px 0' }}>
        <code style={{ color:'#334155', fontSize:'12px', fontFamily:'JetBrains Mono,monospace' }}>{children}</code>
      </pre>
    ),
  blockquote: ({ children }) => (
    <blockquote style={{ borderLeft:'3px solid rgba(30,58,138,0.35)', paddingLeft:'10px', margin:'8px 0', color:'#475569', fontStyle:'italic', fontSize:'13px' }}>
      {children}
    </blockquote>
  ),
  hr: () => <hr style={{ border:'none', borderTop:'1px solid #E2E8F0', margin:'10px 0' }} />,
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
        <div className="max-w-[72%] flex items-start gap-2.5">
          <div className="bg-accent/10 border border-accent/20 rounded-2xl rounded-tr-sm px-4 py-3">
            <p className="text-text text-sm leading-relaxed">{msg.content}</p>
          </div>
          <div className="flex-shrink-0 w-7 h-7 rounded-full bg-muted border border-border flex items-center justify-center mt-1">
            <User size={13} className="text-dim" />
          </div>
        </div>
      </div>
    )
  }

  if (msg.thinking) {
    return (
      <div className="flex items-start gap-3 msg-enter">
        <div className="flex-shrink-0 w-7 h-7 rounded-full bg-accent/10 border border-accent/30 flex items-center justify-center">
          <Bot size={13} className="text-accent animate-pulse-slow" />
        </div>
        <div className="bg-card border border-border rounded-2xl rounded-tl-sm px-4 py-3">
          <div className="flex items-center gap-2 text-dim text-xs font-mono mb-1">
            <Loader2 size={10} className="animate-spin" />
            Running agent pipeline…
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
    <div className="flex items-start gap-3 msg-enter">
      {/* Bot avatar */}
      <div className="flex-shrink-0 w-7 h-7 rounded-full bg-accent/10 border border-accent/30 flex items-center justify-center mt-1">
        <Bot size={13} className="text-accent" />
      </div>

      {/* Bubble */}
      <div className="flex-1 min-w-0 space-y-3">
        {/* Main response card */}
        <div className="bg-card border border-border rounded-2xl rounded-tl-sm px-5 py-4 shadow-card">

          {/* Rich text — takes priority if available */}
          {hasRichText ? (
            <RichTextBlock markdown={msg.richText} />
          ) : (
            <p className="text-text text-sm leading-relaxed">{msg.content}</p>
          )}

          {/* Data table (chart_type === 'table') */}
          {hasTable && (
            <div className="mt-4 pt-4 border-t border-border/60">
              <p className="text-xs font-mono text-dim uppercase tracking-widest mb-2 flex items-center gap-1.5">
                <span className="w-1 h-3 bg-accent rounded-full inline-block" />
                {msg.chartTitle || 'Data Table'}
              </p>
              <DataTable columns={msg.tableData.columns} rows={msg.tableData.rows} />
            </div>
          )}

          {/* Chart */}
          {!hasTable && hasChart && (
            <div className="mt-5 pt-4 border-t border-border/60">
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
          <div className="bg-card border border-border/70 rounded-xl px-5 py-4">
            <div className="flex items-center gap-2 mb-3">
              <Lightbulb size={13} className="text-gold" />
              <span className="text-xs font-mono text-gold uppercase tracking-widest">Recommendations</span>
            </div>
            <div className="space-y-2">
              {msg.recommendations.map((rec, i) => (
                <RecommendationCard key={i} rec={rec} index={i} onAsk={onAsk} />
              ))}
            </div>
          </div>
        )}

        {/* Error */}
        {msg.error && (
          <div className="flex items-start gap-2 px-4 py-3 bg-rose/10 border border-rose/20 rounded-xl">
            <AlertCircle size={13} className="text-rose mt-0.5 flex-shrink-0" />
            <p className="text-rose/80 text-xs font-mono">{msg.error}</p>
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
      className="text-left px-3.5 py-2.5 rounded-xl border border-border bg-card hover:border-accent/40 hover:bg-accent/5 transition-all text-xs text-dim hover:text-text group"
    >
      <span className="text-accent/60 group-hover:text-accent mr-1.5">›</span>
      {text}
    </button>
  )
}

/* ── Chat history indicator ───────────────────── */
function HistoryBadge({ count }) {
  if (count <= 1) return null
  return (
    <div style={{ display:'flex', alignItems:'center', gap:'4px', fontSize:'10px', fontFamily:'JetBrains Mono,monospace', color:'#94a3b8', padding:'2px 7px', background:'#F1F5F9', border:'1px solid #E2E8F0', borderRadius:'999px' }}>
      <History size={9} />
      {count} turns in memory
    </div>
  )
}

/* ── Main Chat ─────────────────────────────────── */
export default function Chat({ suggestions = [] }) {
  const [messages, setMessages]       = useState([])
  const [input, setInput]             = useState('')
  const [loading, setLoading]         = useState(false)
  // Buffer memory: last N turns kept for context
  const [chatHistory, setChatHistory] = useState([])
  const bottomRef                     = useRef(null)
  const inputRef                      = useRef(null)

  const MEMORY_TURNS = 8  // keep last 8 messages (4 user + 4 assistant) in buffer

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Build API-compatible history from chatHistory buffer
  const getHistoryPayload = useCallback(() => {
    return chatHistory.slice(-MEMORY_TURNS)
  }, [chatHistory])

  const sendMessage = async (text) => {
    const question = (text || input).trim()
    if (!question || loading) return

    setInput('')

    // Add user message to display
    const userMsg = { id: Date.now(), role: 'user', content: question }
    setMessages(prev => [...prev, userMsg])

    // Thinking placeholder
    const thinkId = Date.now() + 1
    setMessages(prev => [...prev, { id: thinkId, role: 'assistant', thinking: true, content: '' }])
    setLoading(true)

    // Build history payload (exclude thinking message)
    const historyPayload = getHistoryPayload()

    try {
      const res = await queryAgent(question, historyPayload)

      const assistantContent = res.rich_text || res.summary || 'Analysis complete.'

      setMessages(prev => prev.map(m =>
        m.id === thinkId
          ? {
              id: thinkId,
              role:            'assistant',
              content:         res.summary || 'Analysis complete.',
              richText:        res.rich_text,
              chart:           res.chart,
              chartType:       res.chart_type || 'bar',
              chartTitle:      res.chart_title,
              tableData:       res.table_data,
              recommendations: res.recommendations,
              agentTrace:      res.agent_trace,
              error:           res.error,
              thinking:        false,
            }
          : m
      ))

      // Update buffer memory with this turn
      setChatHistory(prev => [
        ...prev,
        { role: 'user',      content: question },
        { role: 'assistant', content: assistantContent },
      ].slice(-MEMORY_TURNS))

    } catch (err) {
      const message = err?.response?.data?.detail || err.message || 'Connection error.'
      setMessages(prev => prev.map(m =>
        m.id === thinkId
          ? { id: thinkId, role: 'assistant', content: 'Something went wrong.', error: message, thinking: false }
          : m
      ))
    } finally {
      setLoading(false)
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearChat = () => {
    setMessages([])
    setChatHistory([])
  }

  const turnCount = Math.floor(chatHistory.length / 2)
  const isEmpty = messages.length === 0

  return (
    <div className="flex flex-col h-full">

      {/* ── Empty state ─────────────────── */}
      {isEmpty && (
        <div className="flex-1 flex flex-col items-center justify-center px-6 py-12 animate-fade-in">
          <div className="relative mb-6">
            <div className="w-14 h-14 rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center">
              <Sparkles size={24} className="text-accent" />
            </div>
            <div className="absolute -inset-3 rounded-3xl border border-accent/10 animate-pulse-slow" />
          </div>
          <h2 className="font-display text-xl font-bold text-text mb-2 text-center">
            Ask about your campaigns
          </h2>
          <p className="text-dim text-sm text-center mb-8 max-w-sm leading-relaxed">
            Powered by a 4-agent AI pipeline. Ask anything in plain English — follow-up questions understood.
          </p>
          {suggestions.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-xl">
              {suggestions.slice(0, 6).map((s, i) => (
                <SuggestionChip key={i} text={s} onClick={sendMessage} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Messages ────────────────────── */}
      {!isEmpty && (
        <div className="flex-1 overflow-y-auto px-4 py-5 space-y-5">
          {messages.map(msg => <MessageBubble key={msg.id} msg={msg} onAsk={sendMessage} />)}
          <div ref={bottomRef} />
        </div>
      )}

      {/* ── Input bar ───────────────────── */}
      <div className="flex-shrink-0 border-t border-border bg-panel/80 backdrop-blur-md px-4 py-3">
        {/* Suggestion strip after first message */}
        {!isEmpty && suggestions.length > 0 && (
          <div className="flex gap-2 overflow-x-auto pb-2 mb-2 scrollbar-none">
            {suggestions.slice(0, 4).map((s, i) => (
              <button
                key={i}
                onClick={() => sendMessage(s)}
                disabled={loading}
                className="flex-shrink-0 text-xs text-dim border border-border rounded-full px-3 py-1 hover:border-accent/40 hover:text-text transition-all whitespace-nowrap disabled:opacity-40"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        <div className="flex items-end gap-2">
          {/* Left: clear + memory badge */}
          <div className="flex items-center gap-2">
            {!isEmpty && (
              <button
                onClick={clearChat}
                className="flex-shrink-0 w-9 h-9 rounded-xl border border-border hover:border-rose/40 hover:bg-rose/10 flex items-center justify-center text-dim hover:text-rose transition-all"
                title="Clear chat & memory"
              >
                <RefreshCw size={14} />
              </button>
            )}
          </div>

          {/* Textarea */}
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              disabled={loading}
              rows={1}
              placeholder={turnCount > 0 ? "Ask a follow-up question…" : "Ask about campaign performance…"}
              className="w-full bg-card border border-border rounded-xl px-4 py-2.5 text-sm text-text placeholder-dim resize-none focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-all disabled:opacity-50 font-body leading-relaxed"
              style={{ minHeight: '40px', maxHeight: '120px' }}
              onInput={e => {
                e.target.style.height = 'auto'
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
              }}
            />
            {/* Memory indicator inside input area */}
            {turnCount > 0 && (
              <div className="absolute right-3 bottom-2.5 pointer-events-none">
                <HistoryBadge count={turnCount} />
              </div>
            )}
          </div>

          {/* Send button */}
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || loading}
            className="flex-shrink-0 w-9 h-9 rounded-xl bg-accent disabled:bg-muted flex items-center justify-center text-ink disabled:text-dim transition-all hover:bg-accent/80 disabled:cursor-not-allowed"
          >
            {loading
              ? <Loader2 size={14} className="animate-spin text-dim" />
              : <Send size={14} />
            }
          </button>
        </div>
      </div>
    </div>
  )
}