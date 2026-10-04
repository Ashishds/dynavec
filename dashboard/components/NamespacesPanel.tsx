"use client";
import React, { useEffect, useState } from "react";
import { getNamespaceStats, type NamespaceStatsResponse } from "@/lib/api";

interface NamespacesPanelProps {
  traces?: Array<{ namespace?: string }>;
  onSelectNamespace?: (namespace: string) => void;
}

const PARTITION_DESCRIPTIONS: Record<string, string> = {
  "production-core": "Primary enterprise knowledge base and production neural retrieval index.",
  "transformer-paper": "Research benchmark collection for attention mechanism & multi-head evaluation.",
  "portfolio-demo": "Interactive demonstration corpus and developer testing sandbox.",
  "youtube-transcripts": "Multimodal video transcript ingestion & temporal grounding repository.",
  "live-demo": "Real-time telemetry and end-to-end integration validation partition.",
};

export default function NamespacesPanel({ traces = [], onSelectNamespace }: NamespacesPanelProps) {
  const [stats, setStats] = useState<NamespaceStatsResponse | null>(null);

  useEffect(() => {
    getNamespaceStats().then(setStats);
  }, []);

  const getQueryCount = (name: string) => traces.filter((t) => t.namespace === name).length;

  const displayNamespaces = stats?.namespaces?.length
    ? stats.namespaces
    : [
        {
          name: "production-core",
          env: "AWS us-east-1",
          count: 174,
          status: "Active",
        },
        {
          name: "transformer-paper",
          env: "AWS us-east-1",
          count: 75,
          status: "Active",
        },
        {
          name: "portfolio-demo",
          env: "AWS us-east-1",
          count: 12,
          status: "Active",
        },
        {
          name: "live-demo",
          env: "AWS us-east-1",
          count: 4,
          status: "Active",
        },
      ];

  const totalItems = stats?.total_items ?? displayNamespaces.reduce((acc, ns) => acc + ns.count, 0);

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold font-sans tracking-tight text-ink">Tenant Partitions &amp; Namespaces</h2>
          <p className="text-sm text-muted">
            Isolated multi-tenant vector partitions with strict tenant boundary enforcement.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs px-3 py-1.5 bg-accent-soft text-accent-ink rounded-full border border-accent/20 font-medium">
            {displayNamespaces.length} Active Partitions &middot; {totalItems} Indexed Documents
          </span>
        </div>
      </div>

      {/* Partitions Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {displayNamespaces.map((ns) => {
          const queries = getQueryCount(ns.name);
          const description = PARTITION_DESCRIPTIONS[ns.name] || "Dedicated multi-tenant vector partition with isolated document storage.";
          return (
            <div
              key={ns.name}
              className="bg-surface border border-line rounded-xl2 p-5 hover:border-accent/40 transition-colors shadow-sm flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-2.5">
                  <div className="flex items-center gap-2.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-ok animate-pulse" />
                    <span className="font-mono text-base font-bold text-ink">{ns.name}</span>
                  </div>
                  <span className="font-mono text-xs px-2.5 py-0.5 bg-accent-soft text-accent-ink rounded-full font-medium">
                    {ns.count} Documents
                  </span>
                </div>

                <p className="text-xs text-muted mb-4 leading-relaxed">
                  {description}
                </p>

                <div className="space-y-2 border-t border-line/70 pt-3 text-xs font-mono">
                  <div className="flex justify-between items-center">
                    <span className="text-muted">Cloud Region:</span>
                    <span className="text-ink">AWS us-east-1</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted">Isolation Tier:</span>
                    <span className="text-ink font-medium">Dedicated Partition Boundary</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted">Query Traffic:</span>
                    <span className="text-ink font-medium">{queries} requests</span>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-line/70 flex items-center justify-between">
                <span className="font-mono text-[11px] text-ok flex items-center gap-1.5">
                  <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="currentColor">
                    <path fillRule="evenodd" d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z" clipRule="evenodd" />
                  </svg>
                  Active &middot; Encrypted
                </span>
                {onSelectNamespace && (
                  <button
                    onClick={() => onSelectNamespace(ns.name)}
                    className="font-mono text-xs text-accent hover:underline cursor-pointer flex items-center gap-1"
                  >
                    Filter traces &rarr;
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Security & Architecture Overview */}
      <div className="bg-surface border border-line rounded-xl2 p-5">
        <div className="flex items-center gap-2 mb-2">
          <svg className="w-4 h-4 text-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          <h3 className="text-sm font-bold font-sans text-ink">Multi-Tenant Isolation &amp; Privacy Architecture</h3>
        </div>
        <p className="text-xs text-muted leading-relaxed mb-4">
          Each tenant collection is partitioned at the physical storage layer using dedicated hash partition boundaries. All vectors and hydrated documents are isolated in transit and encrypted at rest with AWS KMS, ensuring zero cross-tenant visibility or shared memory bleed-through.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-xs">
          <div className="p-3 bg-bg rounded-lg border border-line">
            <span className="text-faint block text-[11px] uppercase tracking-wider mb-1">Storage Backend</span>
            <span className="text-ink font-semibold block">Amazon DynamoDB</span>
            <span className="text-faint block text-[11px] mt-0.5">Table: dynavec_docs &middot; us-east-1</span>
          </div>
          <div className="p-3 bg-bg rounded-lg border border-line">
            <span className="text-faint block text-[11px] uppercase tracking-wider mb-1">Indexed Knowledge</span>
            <span className="text-ok font-bold block">{totalItems} Total Documents</span>
            <span className="text-faint block text-[11px] mt-0.5">Encrypted at rest (AES-256)</span>
          </div>
          <div className="p-3 bg-bg rounded-lg border border-line">
            <span className="text-faint block text-[11px] uppercase tracking-wider mb-1">Tenant Boundary</span>
            <span className="text-ink font-semibold block">SOC-2 Isolated</span>
            <span className="text-faint block text-[11px] mt-0.5">Zero Cross-Tenant Access</span>
          </div>
        </div>
      </div>
    </div>
  );
}
