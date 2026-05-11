import React, { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Send,
  Loader2,
  Bot,
  User,
  ChevronRight,
  TrendingUp,
  AlertCircle,
  Lightbulb,
  Activity,
  BarChart2,
  Database,
  Brain,
  FileText,
  Sparkles,
  RefreshCw,
  MessageSquare,
  Presentation,
  FileDown,
  Cpu,
  Shield,
  GitMerge,
  Search,
  Scale,
  PenTool,
  CheckCircle2,
  Clock,
} from "lucide-react";
import Chart, { DataTable } from "./Chart.jsx";
import { queryAgent, exportReport, streamQuery } from "../api.js";

/* ── Real Agent metadata (matches backend 9-node pipeline) ────────────────── */
const AGENT_META = {
  planner: {
    label: "Planner",
    color: "text-gold   bg-gold/10   border-gold/20",
    icon: Brain,
  },
  context_resolver: {
    label: "Context Resolver",
    color: "text-indigo bg-indigo/10 border-indigo/20",
    icon: Search,
  },
  kpi_analyst: {
    label: "KPI Analyst",
    color: "text-accent bg-accent/10 border-accent/20",
    icon: BarChart2,
  },
  trend_analyst: {
    label: "Trend Analyst",
    color: "text-sage   bg-sage/10   border-sage/20",
    icon: TrendingUp,
  },
  data_quality_gate: {
    label: "Data Quality Gate",
    color: "text-indigo bg-indigo/10 border-indigo/20",
    icon: Shield,
  },
  synthesizer: {
    label: "Synthesizer",
    color: "text-gold   bg-gold/10   border-gold/20",
    icon: GitMerge,
  },
  strategist: {
    label: "Budget Strategist",
    color: "text-accent bg-accent/10 border-accent/20",
    icon: Scale,
  },
  devils_advocate: {
    label: "Devil's Advocate",
    color: "text-rose   bg-rose/5    border-rose/20",
    icon: AlertCircle,
  },
  report_writer: {
    label: "Report Writer",
    color: "text-text   bg-muted     border-border",
    icon: PenTool,
  },
  // Fallbacks
  supervisor: {
    label: "Supervisor",
    color: "text-gold   bg-gold/10   border-gold/20",
    icon: Cpu,
  },
  data_analyst: {
    label: "Data Analyst",
    color: "text-indigo bg-indigo/10 border-indigo/20",
    icon: Database,
  },
  insight_agent: {
    label: "Insight Agent",
    color: "text-sage   bg-sage/10   border-sage/20",
    icon: Activity,
  },
};

/* ── 7-node pipeline for live visualization ─────────────────────────── */
const PIPELINE_STAGES = [
  {
    id: "planner",
    label: "Planner",
    desc: "Routing query & building execution plan…",
    icon: Brain,
    color: "#D97706",
  },
  {
    id: "context_resolver",
    label: "Context Resolver",
    desc: "Resolving context from conversation history…",
    icon: Search,
    color: "#6366F1",
  },
  {
    id: "kpi_analyst",
    label: "KPI Analyst",
    desc: "Fetching brand uplift, targets & budget data…",
    icon: BarChart2,
    color: "#F59E0B",
  },
  {
    id: "trend_analyst",
    label: "Trend Analyst",
    desc: "Analyzing weekly diagnostics & ad recall…",
    icon: TrendingUp,
    color: "#10B981",
  },
  {
    id: "data_quality",
    label: "Data Quality Gate",
    desc: "Validating completeness & confidence score…",
    icon: Shield,
    color: "#6366F1",
  },
  {
    id: "synthesizer",
    label: "Synthesizer",
    desc: "Cross-correlating patterns across campaigns…",
    icon: GitMerge,
    color: "#D97706",
  },
  {
    id: "strategist",
    label: "Budget Strategist",
    desc: "Generating budget recommendations & scoring…",
    icon: Scale,
    color: "#F59E0B",
  },
  {
    id: "report_writer",
    label: "Report Writer",
    desc: "Compiling final intelligence report…",
    icon: PenTool,
    color: "#332D2D",
  },
];

/* ── Animate pipeline stage durations (ms) ─────────────────────────────────── */
const STAGE_DURATIONS = [1500, 2000, 4000, 4000, 1200, 2800, 2200, 1800];

/* ── Live Pipeline Visualizer ─────────────────── */
// function LivePipeline({ activeStage, completedStages = [] }) {
//   return (
//     <div className="w-full">
//       <div className="flex items-center gap-2 mb-3">
//         <Loader2 size={11} className="animate-spin text-accent" />
//         <span className="text-[10px] font-bold text-dim/70 uppercase tracking-widest">
//           Multi-Agent Pipeline Running
//         </span>
//       </div>
//       <div className="space-y-1">
//         {PIPELINE_STAGES.map((stage) => {
//           const Icon = stage.icon;
//           const isActive = stage.id === activeStage;
//           const isDone = completedStages.includes(stage.id);
//           const isPending = !isActive && !isDone;

//           return (
//             <div
//               key={stage.id}
//               className="flex items-center gap-3 px-3 py-2 rounded-xl transition-all duration-500"
//               style={{
//                 background: isActive
//                   ? `linear-gradient(135deg, ${stage.color}15, ${stage.color}08)`
//                   : isDone
//                     ? "rgba(16,185,129,0.04)"
//                     : "transparent",
//                 border: isActive
//                   ? `1px solid ${stage.color}35`
//                   : isDone
//                     ? "1px solid rgba(16,185,129,0.12)"
//                     : "1px solid transparent",
//                 opacity: isPending ? 0.35 : 1,
//                 transform: isActive ? "translateX(3px)" : "none",
//               }}
//             >
//               {/* Icon */}
//               <div
//                 className="flex-shrink-0 w-6 h-6 rounded-lg flex items-center justify-center"
//                 style={{
//                   background: isActive
//                     ? `${stage.color}22`
//                     : isDone
//                       ? "rgba(16,185,129,0.14)"
//                       : "transparent",
//                 }}
//               >
//                 {isDone ? (
//                   <CheckCircle2 size={12} color="#10B981" />
//                 ) : isActive ? (
//                   <Loader2
//                     size={12}
//                     color={stage.color}
//                     className="animate-spin"
//                   />
//                 ) : (
//                   <Icon size={12} color={isPending ? "#B8AFA8" : stage.color} />
//                 )}
//               </div>

//               {/* Label + desc */}
//               <div className="flex-1 min-w-0">
//                 <div
//                   className="text-[11px] font-bold leading-none truncate"
//                   style={{
//                     color: isActive
//                       ? stage.color
//                       : isDone
//                         ? "#10B981"
//                         : "#B8AFA8",
//                   }}
//                 >
//                   {stage.label}
//                 </div>
//                 {isActive && (
//                   <div className="text-[10px] text-dim/55 leading-none mt-0.5 truncate">
//                     {stage.desc}
//                   </div>
//                 )}
//               </div>

//               {/* Active pulse dots */}
//               {isActive && (
//                 <div className="flex-shrink-0 flex gap-0.5">
//                   {[0, 1, 2].map((i) => (
//                     <span
//                       key={i}
//                       className="w-1 h-1 rounded-full"
//                       style={{
//                         background: stage.color,
//                         opacity: 0.65,
//                         animation: `bounceSoft 0.8s ease-in-out ${i * 0.15}s infinite`,
//                       }}
//                     />
//                   ))}
//                 </div>
//               )}
//             </div>
//           );
//         })}
//       </div>
//     </div>
//   );
// }

/* ── Thinking bubble with live pipeline ───────── */
function ThinkingBubble({ processingStage, completedStages, liveLog = [] }) {
  const [elapsedSecs, setElapsedSecs] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setElapsedSecs((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const currentStageObj = PIPELINE_STAGES.find((s) => s.id === processingStage);

  return (
    <div className="flex items-start gap-4 msg-enter">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center shadow-soft">
        <Bot size={15} className="text-accent" />
      </div>
      <div className="flex-1 bg-white border border-border/60 rounded-2xl rounded-tl-sm px-5 py-4 shadow-card min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Loader2 size={12} className="animate-spin text-accent" />
            <span className="text-[11px] font-bold text-dim uppercase tracking-wider">
              {currentStageObj
                ? `Running: ${currentStageObj.label}`
                : "Processing Intelligence Query"}
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-[10px] font-mono text-dim/50">
            <Clock size={10} />
            {elapsedSecs}s
          </div>
        </div>

        {/* Pipeline */}
        {/* <LivePipeline
          activeStage={processingStage}
          completedStages={completedStages}
        /> */}

        {/* Live terminal feed from backend */}
        {liveLog.length > 0 && (
          <div className="mt-3 rounded-xl border border-border/40 bg-black/20 overflow-hidden">
            <div className="flex items-center gap-2 px-3 py-1.5 border-b border-border/30">
              <Activity size={9} className="text-accent" />
              <span className="text-[9px] font-bold text-dim/60 uppercase tracking-widest">
                Live Agent Log
              </span>
            </div>
            <div className="px-3 py-2 space-y-0.5 max-h-28 overflow-y-auto font-mono">
              {liveLog.map((line, i) => (
                <div
                  key={i}
                  className="text-[9px] text-dim/70 leading-relaxed truncate"
                >
                  {line}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer note */}
        <div className="mt-4 pt-3 border-t border-border/30 flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
          <span className="text-[10px] text-dim/50 font-medium">
            Complex queries run through all agents — this may take 20–40 seconds
          </span>
        </div>
      </div>
    </div>
  );
}

/* ── Recommendation card ──────────────────────── */
function RecommendationCard({ rec, index, onAsk }) {
  return (
    <button
      onClick={() => onAsk(rec)}
      className="w-full text-left flex gap-3.5 p-3.5 rounded-2xl bg-white border border-border/60 shadow-soft hover:shadow-card hover:border-accent/40 hover:bg-accent/[0.02] transition-all group"
      style={{ animationDelay: `${index * 80}ms` }}
    >
      <span className="flex-shrink-0 w-6 h-6 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center text-accent text-xs font-bold group-hover:bg-accent group-hover:text-white group-hover:border-accent transition-all">
        {index + 1}
      </span>
      <p className="text-text/80 text-[13px] font-medium leading-relaxed flex-1">
        {rec}
      </p>
      <span className="flex-shrink-0 text-accent/30 group-hover:text-accent transition-colors self-center text-lg leading-none">
        →
      </span>
    </button>
  );
}

/* ── Rich-text markdown renderer ─────────────── */
const MD_COMPONENTS = {
  h2: React.memo(({ children }) => (
    <h2
      style={{
        fontSize: "16px",
        fontWeight: 700,
        color: "#332D2D",
        marginTop: 0,
        marginBottom: "12px",
        paddingBottom: "8px",
        borderBottom: "1px solid #EDE9E6",
        fontFamily: "Outfit,sans-serif",
        lineHeight: 1.3,
      }}
    >
      {children}
    </h2>
  )),
  h3: React.memo(({ children }) => (
    <h3
      style={{
        fontSize: "14px",
        fontWeight: 600,
        color: "#6366F1",
        marginTop: "16px",
        marginBottom: "8px",
        fontFamily: "Outfit,sans-serif",
      }}
    >
      {children}
    </h3>
  )),
  p: React.memo(({ children }) => (
    <p
      style={{
        fontSize: "14px",
        color: "#4B443F",
        lineHeight: 1.6,
        marginBottom: "12px",
        marginTop: 0,
      }}
    >
      {children}
    </p>
  )),
  strong: React.memo(({ children }) => (
    <strong style={{ color: "#332D2D", fontWeight: 700 }}>{children}</strong>
  )),
  em: React.memo(({ children }) => (
    <em style={{ color: "#D97706", fontStyle: "italic", fontWeight: 500 }}>
      {children}
    </em>
  )),
  ul: React.memo(({ children }) => (
    <ul style={{ margin: "0 0 12px 0", padding: 0, listStyle: "none" }}>
      {children}
    </ul>
  )),
  ol: React.memo(({ children }) => (
    <ol style={{ margin: "0 0 12px 0", paddingLeft: "20px" }}>{children}</ol>
  )),
  li: React.memo(({ children }) => (
    <li
      style={{
        display: "flex",
        gap: "10px",
        fontSize: "14px",
        color: "#4B443F",
        lineHeight: 1.6,
        marginBottom: "6px",
      }}
    >
      <span
        style={{
          color: "#F59E0B",
          marginTop: "4px",
          flexShrink: 0,
          fontSize: "16px",
          lineHeight: 1,
        }}
      >
        •
      </span>
      <span>{children}</span>
    </li>
  )),
  table: React.memo(({ children }) => (
    <div
      style={{
        overflowX: "auto",
        borderRadius: "12px",
        border: "1px solid #EDE9E6",
        margin: "16px 0",
        boxShadow: "0 4px 12px rgba(45,40,37,0.04)",
      }}
    >
      <table
        style={{
          width: "100%",
          fontSize: "12.5px",
          borderCollapse: "collapse",
          tableLayout: "auto",
        }}
      >
        {children}
      </table>
    </div>
  )),
  thead: React.memo(({ children }) => (
    <thead style={{ background: "#FDFCFB", borderBottom: "1px solid #EDE9E6" }}>
      {children}
    </thead>
  )),
  tbody: React.memo(({ children }) => <tbody>{children}</tbody>),
  tr: React.memo(({ children }) => (
    <tr style={{ borderBottom: "1px solid rgba(237,233,230,0.6)" }}>
      {children}
    </tr>
  )),
  th: React.memo(({ children }) => (
    <th
      style={{
        padding: "10px 14px",
        textAlign: "left",
        color: "#7C726A",
        textTransform: "uppercase",
        letterSpacing: "0.05em",
        fontWeight: 700,
        whiteSpace: "nowrap",
        fontSize: "10px",
      }}
    >
      {children}
    </th>
  )),
  td: React.memo(({ children }) => (
    <td
      style={{
        padding: "10px 14px",
        color: "#4B443F",
        whiteSpace: "normal",
        wordBreak: "break-word",
      }}
    >
      {children}
    </td>
  )),
  code: ({ inline, children }) =>
    inline ? (
      <code
        style={{
          background: "#F3F1EF",
          color: "#6366F1",
          fontSize: "12px",
          padding: "2px 6px",
          borderRadius: "6px",
          fontFamily: "JetBrains Mono,monospace",
          fontWeight: 500,
        }}
      >
        {children}
      </code>
    ) : (
      <pre
        style={{
          background: "#FFFFFF",
          border: "1px solid #EDE9E6",
          borderRadius: "12px",
          padding: "14px",
          overflowX: "auto",
          margin: "12px 0",
        }}
      >
        <code
          style={{
            color: "#4B443F",
            fontSize: "12.5px",
            fontFamily: "JetBrains Mono,monospace",
            lineHeight: 1.5,
          }}
        >
          {children}
        </code>
      </pre>
    ),
  blockquote: ({ children }) => (
    <blockquote
      style={{
        borderLeft: "4px solid #F59E0B",
        padding: "12px 16px",
        margin: "16px 0",
        color: "#7C726A",
        fontStyle: "italic",
        fontSize: "14px",
        background: "rgba(245,158,11,0.03)",
        borderRadius: "0 12px 12px 0",
      }}
    >
      {children}
    </blockquote>
  ),
  hr: () => (
    <hr
      style={{
        border: "none",
        borderTop: "1px solid #EDE9E6",
        margin: "16px 0",
      }}
    />
  ),
};

function RichTextBlock({ markdown }) {
  if (!markdown) return null;
  return (
    <div style={{ lineHeight: 1.6 }}>
      <ReactMarkdown components={MD_COMPONENTS} remarkPlugins={[remarkGfm]}>
        {markdown}
      </ReactMarkdown>
    </div>
  );
}

/* ── Single message bubble ────────────────────── */
function MessageBubble({ msg, onAsk }) {
  const isUser = msg.role === "user";
  const [exporting, setExporting] = useState(null);

  const handleExport = async (format) => {
    try {
      setExporting(format);
      const payload = {
        format,
        summary: msg.content || "",
        rich_text: msg.richText || "",
        chart_data: msg.chart || null,
        chart_title: msg.chartTitle || "",
        table_data: msg.tableData || null,
      };
      const blob = await exportReport(payload);
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute(
        "download",
        `report.${format === "ppt" ? "pptx" : "docx"}`,
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error("Export failed:", err);
      alert("Export failed. Please try again.");
    } finally {
      setExporting(null);
    }
  };

  if (isUser) {
    return (
      <div className="flex justify-end msg-enter">
        <div className="max-w-[75%] flex items-start gap-3">
          <div className="bg-indigo/10 border border-indigo/20 rounded-2xl rounded-tr-sm px-4 py-3 shadow-soft">
            <p className="text-text text-[14px] font-medium leading-relaxed">
              {msg.content}
            </p>
          </div>
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-white border border-border shadow-soft flex items-center justify-center mt-1">
            <User size={14} className="text-indigo" />
          </div>
        </div>
      </div>
    );
  }

  const hasRichText = !!msg.richText;
  const chartType = msg.chartType || "bar";
  const hasChart =
    chartType !== "none" && chartType !== "table" && msg.chart?.length > 0;
  const hasTable = chartType === "table" && msg.tableData?.columns?.length > 0;
  const hasStandaloneTable = !hasTable && msg.tableData?.columns?.length > 0;

  return (
    <div className="flex items-start gap-4 msg-enter">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center mt-1 shadow-soft">
        <Bot size={15} className="text-accent" />
      </div>

      <div className="flex-1 min-w-0 space-y-4">
        <div className="bg-white border border-border/60 rounded-2xl rounded-tl-sm px-6 py-5 shadow-card relative group/card">
          {/* Export Actions */}
          {!msg.error && (
            <div className="absolute top-4 right-4 flex items-center gap-2 opacity-0 group-hover/card:opacity-100 transition-opacity">
              <button
                onClick={() => handleExport("docx")}
                disabled={!!exporting}
                className="p-2 rounded-lg bg-white border border-border/60 text-dim hover:text-indigo hover:border-indigo/30 hover:bg-indigo/5 transition-all shadow-soft flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider"
                title="Export as Word"
              >
                {exporting === "docx" ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <FileDown size={12} />
                )}
                DOCX
              </button>
              <button
                onClick={() => handleExport("ppt")}
                disabled={!!exporting}
                className="p-2 rounded-lg bg-white border border-border/60 text-dim hover:text-gold hover:border-gold/30 hover:bg-gold/5 transition-all shadow-soft flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider"
                title="Export as PowerPoint"
              >
                {exporting === "ppt" ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <Presentation size={12} />
                )}
                PPT
              </button>
            </div>
          )}

          {msg.content && (
            <div className="mb-4 px-4 py-3 rounded-xl bg-accent/5 border border-accent/15">
              <p className="text-text text-[13.5px] leading-relaxed font-semibold">
                {msg.content}
              </p>
            </div>
          )}

          {hasRichText && <RichTextBlock markdown={msg.richText} />}

          {hasTable && (
            <div className="mt-6 pt-5 border-t border-border/40">
              <p className="text-[10px] font-bold text-dim uppercase tracking-wider mb-3 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                {msg.chartTitle || "Data Table"}
              </p>
              <DataTable
                columns={msg.tableData.columns}
                rows={msg.tableData.rows}
              />
            </div>
          )}

          {hasStandaloneTable && (
            <div className="mt-6 pt-5 border-t border-border/40">
              <p className="text-[10px] font-bold text-dim uppercase tracking-wider mb-3 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo" />
                Supporting Data
              </p>
              <DataTable
                columns={msg.tableData.columns}
                rows={msg.tableData.rows}
              />
            </div>
          )}

          {hasChart && (
            <div className="mt-6 pt-5 border-t border-border/40">
              <Chart
                data={msg.chart}
                type={chartType}
                title={msg.chartTitle}
                tableData={msg.tableData}
              />
            </div>
          )}
        </div>

        {msg.recommendations?.length > 0 && (
          <div className="bg-white/40 border border-border/40 rounded-2xl px-6 py-5">
            <div className="flex items-center gap-2.5 mb-4">
              <div className="p-1.5 rounded-lg bg-gold/10">
                <Lightbulb size={14} className="text-gold" />
              </div>
              <span className="text-[11px] font-bold text-gold uppercase tracking-wider">
                Suggested Insights
              </span>
            </div>
            <div className="space-y-3">
              {msg.recommendations.map((rec, i) => (
                <RecommendationCard key={i} rec={rec} index={i} onAsk={onAsk} />
              ))}
            </div>
          </div>
        )}

        {msg.error && (
          <div className="flex items-start gap-3 px-5 py-4 bg-rose/5 border border-rose/20 rounded-2xl">
            <AlertCircle size={15} className="text-rose mt-0.5 flex-shrink-0" />
            <p className="text-rose/80 text-[13px] font-medium leading-relaxed">
              {msg.error}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Suggestion chip ──────────────────────────── */
function SuggestionChip({ text, onClick }) {
  return (
    <button
      onClick={() => onClick(text)}
      className="text-left px-4 py-3 rounded-2xl border border-border bg-white shadow-soft hover:shadow-card hover:border-accent/40 hover:bg-accent/[0.02] transition-all text-[13px] font-medium text-text/70 hover:text-text group flex items-center gap-2"
    >
      <Sparkles
        size={13}
        className="text-accent/40 group-hover:text-accent transition-colors"
      />
      {text}
    </button>
  );
}

/* ── Pipeline stage tracker — driven by REAL SSE from backend ─────── */
function usePipelineSimulator(isLoading, question = "") {
  const [activeStage, setActiveStage] = useState(null);
  const [completedStages, setCompletedStages] = useState([]);
  const [liveLog, setLiveLog] = useState([]);
  const esRef = useRef(null);
  const timerRef = useRef(null);
  const stageIdxRef = useRef(0);

  // Map backend node names to PIPELINE_STAGES ids
  const nodeToStage = {
    "[PLANNER]": "planner",
    "[CONTEXT_RESOLVER]": "context_resolver",
    "[KPI_ANALYST]": "kpi_analyst",
    "[TREND_ANALYST]": "trend_analyst",
    "[DATA_QUALITY_GATE]": "data_quality_gate",
    "[SYNTHESIZER]": "synthesizer",
    "[STRATEGIST]": "strategist",
    "[REPORT_WRITER]": "report_writer",
  };

  useEffect(() => {
    if (!isLoading) {
      setActiveStage(null);
      setCompletedStages([]);
      setLiveLog([]);
      stageIdxRef.current = 0;
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
      if (timerRef.current) clearTimeout(timerRef.current);
      return;
    }

    setActiveStage(PIPELINE_STAGES[0].id);
    setCompletedStages([]);
    setLiveLog([]);
    stageIdxRef.current = 0;

    if (!question) {
      // Fallback: simulated timer progression
      function advance() {
        stageIdxRef.current += 1;
        if (stageIdxRef.current >= PIPELINE_STAGES.length) return;
        const prev = PIPELINE_STAGES[stageIdxRef.current - 1].id;
        const curr = PIPELINE_STAGES[stageIdxRef.current].id;
        setCompletedStages((cs) => [...cs, prev]);
        setActiveStage(curr);
        timerRef.current = setTimeout(
          advance,
          STAGE_DURATIONS[stageIdxRef.current],
        );
      }
      timerRef.current = setTimeout(advance, STAGE_DURATIONS[0]);
      return;
    }

    // Real SSE stream from backend
    const es = streamQuery(
      question,
      (line) => {
        setLiveLog((l) => [...l.slice(-20), line]);
        // Detect which node just started from the log line
        for (const [prefix, stageId] of Object.entries(nodeToStage)) {
          if (line.startsWith(prefix)) {
            setCompletedStages((cs) => {
              const idx = PIPELINE_STAGES.findIndex((s) => s.id === stageId);
              const done = PIPELINE_STAGES.slice(0, idx).map((s) => s.id);
              return done;
            });
            setActiveStage(stageId);
            break;
          }
        }
      },
      () => {
        setCompletedStages(PIPELINE_STAGES.map((s) => s.id));
        setActiveStage(null);
      },
    );
    esRef.current = es;

    return () => {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [isLoading, question]);

  return { activeStage, completedStages, liveLog };
}

/* ── Main Chat ─────────────────────────────────── */
export default function Chat({ suggestions = [] }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState("");
  const chatEndRef = useRef(null);
  const { activeStage, completedStages, liveLog } = usePipelineSimulator(
    loading,
    currentQuestion,
  );

  const scrollToBottom = useCallback(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, activeStage, scrollToBottom]);

  const onSend = async (text = input) => {
    if (!text.trim() || loading) return;

    const currentHistory = messages.map((m) => ({
      role: m.role,
      content: m.content || "",
    }));

    const userMsg = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setCurrentQuestion(text);
    setInput("");
    setLoading(true);

    try {
      const res = await queryAgent(text, currentHistory);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.content || res.summary || "Analysis complete.",
          richText: res.rich_text,
          agentTrace: res.agent_trace,
          chart: res.chart,
          chartType: res.chart_type,
          chartTitle: res.chart_title,
          tableData: res.table_data,
          recommendations: res.recommendations,
        },
      ]);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: detail
            ? `Sorry, I encountered an error: ${detail}`
            : "Sorry, I encountered an error.",
          error: detail,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

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
              <h2 className="text-2xl font-display font-bold text-text mb-3 tracking-tight">
                How can I help you today?
              </h2>
              <p className="text-text/60 text-base font-medium max-w-md mx-auto">
                Ask about campaign performance, budget allocation, segment
                insights, or trend analysis across all RetailCo campaigns.
              </p>
            </div>

            <div className="w-full pt-4">
              <p className="text-[10px] font-bold text-dim/50 uppercase tracking-[0.2em] mb-6">
                Popular starting points
              </p>
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

        {/* Live pipeline visualizer while loading */}
        {loading && (
          <ThinkingBubble
            processingStage={activeStage}
            completedStages={completedStages}
            liveLog={liveLog}
          />
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input area */}
      <div className="flex-shrink-0 p-6 pt-0">
        <div className="max-w-4xl mx-auto relative">
          <div className="bg-white border border-border shadow-card rounded-[24px] p-2 flex items-center gap-2 focus-within:border-accent/40 focus-within:shadow-accent/5 transition-all">
            <div className="flex-shrink-0 pl-3 text-dim/40">
              <RefreshCw
                size={18}
                className={loading ? "animate-spin text-accent" : ""}
              />
            </div>
            <input
              className="flex-1 bg-transparent border-none outline-none text-[15px] font-medium text-text placeholder:text-text/30 py-3 px-1"
              placeholder="Ask anything about your campaigns…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onSend()}
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
            Agent LangGraph Pipeline · RetailCo Intelligence Hub
          </p>
        </div>
      </div>
    </div>
  );
}
