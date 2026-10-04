import React, { memo } from "react";
import { Handle, Position, NodeProps } from "reactflow";
import { AgentNodeData, NodeType } from "./types";

interface NodeTheme {
  icon: string;
  badge: string;
  borderColor: string;
  bgLight: string;
  accentColor: string;
}

const THEMES: Record<NodeType, NodeTheme> = {
  retriever: {
    icon: "DB",
    badge: "Dynavec Vector",
    borderColor: "border-sky-500/40 hover:border-sky-500",
    bgLight: "bg-sky-500/10 text-sky-400",
    accentColor: "#0284c7",
  },
  llm: {
    icon: "LLM",
    badge: "LLM Synthesizer",
    borderColor: "border-accent/40 hover:border-accent",
    bgLight: "bg-accent-soft text-accent-ink",
    accentColor: "#e8623b",
  },
  guard: {
    icon: "GRD",
    badge: "Safety Guard",
    borderColor: "border-emerald-500/40 hover:border-emerald-500",
    bgLight: "bg-emerald-500/10 text-emerald-400",
    accentColor: "#10b981",
  },
  classifier: {
    icon: "RTR",
    badge: "Intent Router",
    borderColor: "border-purple-500/40 hover:border-purple-500",
    bgLight: "bg-purple-500/10 text-purple-400",
    accentColor: "#8b5cf6",
  },
  reranker: {
    icon: "RNK",
    badge: "Reranker",
    borderColor: "border-teal-500/40 hover:border-teal-500",
    bgLight: "bg-teal-500/10 text-teal-400",
    accentColor: "#14b8a6",
  },
  cache: {
    icon: "RNK",
    badge: "Semantic Cache",
    borderColor: "border-amber-500/40 hover:border-amber-500",
    bgLight: "bg-amber-500/10 text-amber-400",
    accentColor: "#f59e0b",
  },
  eval: {
    icon: "EVL",
    badge: "Ragas Metric",
    borderColor: "border-rose-500/40 hover:border-rose-500",
    bgLight: "bg-rose-500/10 text-rose-400",
    accentColor: "#f43f5e",
  },
  code: {
    icon: "PY",
    badge: "Python Code",
    borderColor: "border-indigo-500/40 hover:border-indigo-500",
    bgLight: "bg-indigo-500/10 text-indigo-400",
    accentColor: "#6366f1",
  },
  http: {
    icon: "API",
    badge: "HTTP / Webhook",
    borderColor: "border-blue-500/40 hover:border-blue-500",
    bgLight: "bg-blue-500/10 text-blue-400",
    accentColor: "#3b82f6",
  },
  response: {
    icon: "OUT",
    badge: "Output Deliver",
    borderColor: "border-emerald-500/40 hover:border-emerald-500",
    bgLight: "bg-emerald-500/10 text-emerald-400",
    accentColor: "#10b981",
  },
};

export const AgentNodeComponent = memo(({ id, data, selected }: NodeProps<AgentNodeData>) => {
  const theme = THEMES[data.type] || THEMES.retriever;
  const status = data.status || "idle";

  // Summarize primary config fields for node display
  const renderConfigBadges = () => {
    const cfg = data.config || {};
    const badges: string[] = [];

    if (data.type === "retriever") {
      if (cfg.namespace) badges.push(`ns: ${cfg.namespace}`);
      if (cfg.top_k) badges.push(`k: ${cfg.top_k}`);
      if (cfg.metric) badges.push(cfg.metric);
    } else if (data.type === "llm") {
      if (cfg.model) badges.push(cfg.model);
      if (cfg.temperature !== undefined) badges.push(`T: ${cfg.temperature}`);
    } else if (data.type === "guard") {
      if (cfg.threshold) badges.push(`> ${cfg.threshold}`);
      if (cfg.metric_name) badges.push(cfg.metric_name);
    } else if (data.type === "classifier") {
      if (cfg.categories) badges.push(`${cfg.categories.length} routes`);
    } else if (data.type === "reranker") {
      if (cfg.top_n) badges.push(`top ${cfg.top_n}`);
    } else if (data.type === "cache") {
      if (cfg.similarity_threshold) badges.push(`> ${cfg.similarity_threshold}`);
    } else if (data.type === "eval") {
      if (cfg.metrics) badges.push(Array.isArray(cfg.metrics) ? cfg.metrics.join(", ") : cfg.metrics);
    }

    if (badges.length === 0) return null;

    return (
      <div className="flex flex-wrap gap-1 mt-2.5">
        {badges.map((b, i) => (
          <span
            key={i}
            className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-bg text-muted border border-line"
          >
            {b}
          </span>
        ))}
      </div>
    );
  };

  return (
    <div
      className={`relative min-w-[260px] max-w-[310px] rounded-xl border bg-surface p-3.5 shadow-md transition-all ${
        selected ? "ring-2 ring-accent border-accent shadow-xl scale-[1.02]" : theme.borderColor
      } ${
        status === "running" ? "ring-2 ring-amber-400 animate-pulse border-amber-400" : ""
      } ${status === "success" ? "ring-1 ring-emerald-500/80 border-emerald-500/80" : ""} ${
        status === "error" ? "ring-2 ring-err border-err" : ""
      }`}
    >
      {/* Target Handle (Input) — unless it's a pure trigger / cache node without input */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !-left-2 !bg-accent hover:!scale-125 transition-transform"
      />

      {/* Header */}
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-2">
          <span className="text-base select-none">{theme.icon}</span>
          <span className={`text-[10.5px] font-mono uppercase font-semibold px-1.5 py-0.5 rounded border border-transparent ${theme.bgLight}`}>
            {theme.badge}
          </span>
        </div>

        {/* Execution status indicator */}
        <div className="flex items-center gap-1.5">
          {status === "running" && (
            <span className="flex items-center gap-1 font-mono text-[10px] text-amber-500 font-medium">
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping inline-block" />
              RUNNING
            </span>
          )}
          {status === "success" && (
            <span className="flex items-center gap-1 font-mono text-[10px] text-emerald-500 font-medium">
              <svg className="w-3 h-3 text-emerald-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
              </svg>
              <span>{data.executionTimeMs ? `${data.executionTimeMs}ms` : "OK"}</span>
            </span>
          )}
          {status === "error" && (
            <span className="flex items-center gap-1 font-mono text-[10px] text-err font-medium">
              <svg className="w-3 h-3 text-err shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
              </svg>
              <span>FAILED</span>
            </span>
          )}
          {status === "idle" && (
            <span className="w-2 h-2 rounded-full bg-faint/40 inline-block" />
          )}
        </div>
      </div>

      {/* Title & description */}
      <div className="mt-1">
        <h3 className="font-semibold text-[13.5px] text-ink leading-tight">
          {data.label}
        </h3>
        <p className="text-[11.5px] text-muted line-clamp-2 mt-0.5 leading-snug">
          {data.description}
        </p>
      </div>

      {/* Config Badges */}
      {renderConfigBadges()}

      {/* Execution Output preview if available */}
      {data.lastOutput && (
        <div className="mt-2.5 pt-2 border-t border-line/60">
          <div className="flex items-center justify-between text-[10px] font-mono text-faint mb-1">
            <span>Last Output:</span>
            <span>{typeof data.lastOutput === "object" ? Object.keys(data.lastOutput).length + " keys" : "string"}</span>
          </div>
          <div className="font-mono text-[10px] text-ink/80 bg-bg p-1.5 rounded max-h-16 overflow-y-auto truncate border border-line">
            {typeof data.lastOutput === "object"
              ? JSON.stringify(data.lastOutput, null, 2)
              : String(data.lastOutput)}
          </div>
        </div>
      )}

      {/* Specialized Multi-Handles for Condition / Branching Nodes */}
      {data.type === "guard" && (
        <>
          <div className="mt-2 pt-2 border-t border-line flex justify-between text-[10px] font-mono">
            <span className="text-emerald-500 flex items-center gap-1">
              ● Pass
            </span>
            <span className="text-rose-500 flex items-center gap-1">
              Fail / Block ●
            </span>
          </div>
          <Handle
            id="pass"
            type="source"
            position={Position.Right}
            style={{ top: "45%" }}
            className="!w-3 !h-3 !-right-2 !bg-emerald-500 hover:!scale-125"
          />
          <Handle
            id="fail"
            type="source"
            position={Position.Right}
            style={{ top: "85%" }}
            className="!w-3 !h-3 !-right-2 !bg-rose-500 hover:!scale-125"
          />
        </>
      )}

      {data.type === "cache" && (
        <>
          <div className="mt-2 pt-2 border-t border-line flex justify-between text-[10px] font-mono">
            <span className="text-emerald-500">● Cache Hit</span>
            <span className="text-muted">Miss ●</span>
          </div>
          <Handle
            id="hit"
            type="source"
            position={Position.Right}
            style={{ top: "45%" }}
            className="!w-3 !h-3 !-right-2 !bg-emerald-500 hover:!scale-125"
          />
          <Handle
            id="miss"
            type="source"
            position={Position.Right}
            style={{ top: "85%" }}
            className="!w-3 !h-3 !-right-2 !bg-muted hover:!scale-125"
          />
        </>
      )}

      {data.type === "eval" && (
        <>
          <div className="mt-2 pt-2 border-t border-line flex justify-between text-[10px] font-mono">
            <span className="text-emerald-500">● Qualified</span>
            <span className="text-amber-500">Retry loop ●</span>
          </div>
          <Handle
            id="pass"
            type="source"
            position={Position.Right}
            style={{ top: "45%" }}
            className="!w-3 !h-3 !-right-2 !bg-emerald-500 hover:!scale-125"
          />
          <Handle
            id="fail"
            type="source"
            position={Position.Right}
            style={{ top: "85%" }}
            className="!w-3 !h-3 !-right-2 !bg-amber-500 hover:!scale-125"
          />
        </>
      )}

      {data.type === "classifier" && (
        <>
          <div className="mt-2 pt-2 border-t border-line flex flex-col gap-1 text-[10px] font-mono">
            {(data.config.categories || ["route-0", "route-1"]).map((c: string, idx: number) => (
              <div key={idx} className="flex justify-between items-center text-muted">
                <span className="truncate max-w-[150px]">{c}</span>
                <span className="text-accent text-[9px]">● handle {idx}</span>
              </div>
            ))}
          </div>
          {(data.config.categories || ["route-0", "route-1"]).map((_: string, idx: number) => {
            const count = (data.config.categories || ["route-0", "route-1"]).length;
            const topPct = 30 + ((idx + 1) / (count + 1)) * 60;
            return (
              <Handle
                key={idx}
                id={`route-${idx}`}
                type="source"
                position={Position.Right}
                style={{ top: `${topPct}%` }}
                className="!w-3 !h-3 !-right-2 !bg-purple-500 hover:!scale-125"
              />
            );
          })}
        </>
      )}

      {/* Standard single source handle for non-branching nodes */}
      {!["guard", "cache", "eval", "classifier", "response"].includes(data.type) && (
        <Handle
          type="source"
          position={Position.Right}
          className="!w-3 !h-3 !-right-2 !bg-accent hover:!scale-125 transition-transform"
        />
      )}
    </div>
  );
});

AgentNodeComponent.displayName = "AgentNodeComponent";

export const nodeTypes = {
  agentNode: AgentNodeComponent,
};
