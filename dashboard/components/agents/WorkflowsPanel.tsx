"use client";

import React from "react";
import { DEFAULT_TEMPLATES } from "./defaultGraphs";

interface WorkflowsPanelProps {
  onOpenCanvas: (templateId?: string) => void;
  onNavigateToTracing: () => void;
}

export default function WorkflowsPanel({
  onOpenCanvas,
  onNavigateToTracing,
}: WorkflowsPanelProps) {
  const workflows = [
    {
      id: "enterprise-rag-guardrails",
      name: "Enterprise RAG with Guardrails",
      description: "Production retrieval augmented generation with DynamoDB semantic caching, Dynavec vector search, confidence threshold guard, and LLM synthesis.",
      status: "Production",
      category: "RAG",
      nodes: 6,
      latency: "142ms",
      successRate: "99.4%",
      runsLast24h: 12480,
      updated: "10 mins ago",
    },
    {
      id: "self-reflective-rag",
      name: "Self-Reflective RAG (Inline Eval Loop)",
      description: "Evaluates LLM generation against retrieved context with RAGAS faithfulness metrics. Automatically retries if hallucination is detected.",
      status: "Active",
      category: "Evaluation",
      nodes: 4,
      latency: "320ms",
      successRate: "98.1%",
      runsLast24h: 3410,
      updated: "2 hours ago",
    },
    {
      id: "multi-agent-router",
      name: "Intent Classifier & Multi-Agent Router",
      description: "Semantically classifies inbound query and branches execution into technical docs, transactional billing API, or general support flow.",
      status: "Testing",
      category: "Autonomous",
      nodes: 5,
      latency: "98ms",
      successRate: "96.8%",
      runsLast24h: 890,
      updated: "Yesterday",
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-line pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-accent font-semibold uppercase tracking-wider">
              Agent Studio
            </span>
            <span className="text-faint text-xs">/</span>
            <span className="font-mono text-xs text-muted">Workflows</span>
          </div>
          <h1 className="text-2xl font-bold text-ink mt-1 font-sans">
            Agent Orchestration Workflows
          </h1>
          <p className="text-sm text-muted mt-0.5 font-sans">
            Design, deploy, and monitor directed acyclic graph (DAG) agent pipelines powered by dynavec vector search.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onOpenCanvas()}
            className="py-2 px-4 rounded-lg text-xs font-mono font-semibold bg-accent text-white hover:bg-accent/90 shadow-sm transition-all cursor-pointer"
          >
            + New Pipeline Graph
          </button>
        </div>
      </div>

      {/* Overview KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-4 rounded-xl border border-line bg-surface">
          <span className="text-xs font-mono text-muted uppercase">Active Workflows</span>
          <div className="text-2xl font-bold text-ink font-mono mt-1">3</div>
          <span className="text-[11px] text-emerald-500 font-mono mt-0.5 block">100% operational</span>
        </div>
        <div className="p-4 rounded-xl border border-line bg-surface">
          <span className="text-xs font-mono text-muted uppercase">Total Invocations (24h)</span>
          <div className="text-2xl font-bold text-ink font-mono mt-1">16,780</div>
          <span className="text-[11px] text-emerald-500 font-mono mt-0.5 block">+18.4% vs yesterday</span>
        </div>
        <div className="p-4 rounded-xl border border-line bg-surface">
          <span className="text-xs font-mono text-muted uppercase">Avg Graph Latency</span>
          <div className="text-2xl font-bold text-ink font-mono mt-1">186ms</div>
          <span className="text-[11px] text-muted font-mono mt-0.5 block">p95: 340ms</span>
        </div>
        <div className="p-4 rounded-xl border border-line bg-surface">
          <span className="text-xs font-mono text-muted uppercase">Guardrail Pass Rate</span>
          <div className="text-2xl font-bold text-emerald-500 font-mono mt-1">98.9%</div>
          <span className="text-[11px] text-faint font-mono mt-0.5 block">1.1% blocked/fallback</span>
        </div>
      </div>

      {/* Workflow Cards */}
      <div className="space-y-4">
        <h2 className="text-sm font-mono uppercase tracking-wider text-muted font-semibold">
          Deployed Agent Graphs
        </h2>

        <div className="grid grid-cols-1 gap-4">
          {workflows.map((wf) => (
            <div
              key={wf.id}
              className="p-5 rounded-xl border border-line bg-surface hover:border-accent/40 transition-all shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-2 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-accent px-1.5 py-0.5 rounded bg-accent-soft">ACTIVE</span>
                  <h3 className="font-bold text-base text-ink">{wf.name}</h3>
                  <span
                    className={`font-mono text-[10.5px] px-2 py-0.5 rounded-full font-semibold border ${
                      wf.status === "Production"
                        ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                        : wf.status === "Active"
                        ? "bg-blue-500/10 text-blue-500 border-blue-500/20"
                        : "bg-amber-500/10 text-amber-500 border-amber-500/20"
                    }`}
                  >
                    ● {wf.status}
                  </span>
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-bg text-muted border border-line">
                    {wf.category}
                  </span>
                </div>
                <p className="text-xs text-muted leading-relaxed max-w-3xl">
                  {wf.description}
                </p>
                <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-faint pt-1">
                  <span>{wf.nodes} Nodes in Graph</span>
                  <span>·</span>
                  <span className="text-ink font-medium">{wf.latency} avg latency</span>
                  <span>·</span>
                  <span className="text-emerald-500 font-medium">{wf.successRate} success</span>
                  <span>·</span>
                  <span>{wf.runsLast24h.toLocaleString()} runs / 24h</span>
                  <span>·</span>
                  <span>Updated {wf.updated}</span>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 self-start md:self-center shrink-0">
                <button
                  type="button"
                  onClick={() => onNavigateToTracing()}
                  className="py-2 px-3 rounded-lg text-xs font-mono border border-line bg-bg hover:bg-surface text-muted hover:text-ink transition-colors"
                >
                  View Traces
                </button>
                <button
                  type="button"
                  onClick={() => onOpenCanvas(wf.id)}
                  className="py-2 px-4 rounded-lg text-xs font-mono font-semibold bg-accent text-white hover:bg-accent/90 transition-all flex items-center gap-1.5 cursor-pointer shadow-sm"
                >
                  <span>Open in Canvas</span>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Ready-Made Blueprints */}
      <div className="mt-8 pt-6 border-t border-line space-y-3">
        <h3 className="text-sm font-mono uppercase tracking-wider text-muted font-semibold">
          Starter Blueprints
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {DEFAULT_TEMPLATES.map((tmpl) => (
            <div
              key={tmpl.id}
              className="p-4 rounded-xl border border-line bg-bg/50 hover:bg-surface hover:border-accent/30 transition-all flex flex-col justify-between"
            >
              <div>
                <span className="font-mono text-[10px] text-accent uppercase font-semibold">
                  {tmpl.category}
                </span>
                <h4 className="font-bold text-sm text-ink mt-0.5">{tmpl.name}</h4>
                <p className="text-xs text-muted mt-1 line-clamp-2 leading-relaxed">
                  {tmpl.description}
                </p>
              </div>
              <button
                type="button"
                onClick={() => onOpenCanvas(tmpl.id)}
                className="mt-3 text-xs font-mono font-medium text-accent hover:underline flex items-center gap-1 cursor-pointer"
              >
                <span>Launch Blueprint</span>
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
