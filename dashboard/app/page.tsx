"use client";
import { useCallback, useEffect, useState } from "react";
import EvalTrends from "@/components/EvalTrends";
import Kpis from "@/components/Kpis";
import LatencyChart from "@/components/LatencyChart";
import LatencyPanel from "@/components/LatencyPanel";
import CostPanel from "@/components/CostPanel";
import ResourcesPanel from "@/components/ResourcesPanel";
import NamespacesPanel from "@/components/NamespacesPanel";
import FaithfulnessPanel from "@/components/FaithfulnessPanel";
import SearchPlayground from "@/components/SearchPlayground";
import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import TraceDrawer from "@/components/TraceDrawer";
import TracesTable from "@/components/TracesTable";
import VolumeChart from "@/components/VolumeChart";
import { getEvalRuns, getMetrics, getTrace, getTraces, isLive } from "@/lib/api";
import type { EvalRun, Metrics, TraceEvent, TraceFilters } from "@/lib/types";
import LandingPage from "@/components/LandingPage";
import AgentCanvas from "@/components/agents/AgentCanvas";
import WorkflowsPanel from "@/components/agents/WorkflowsPanel";
import TestSuitePanel from "@/components/agents/TestSuitePanel";

export default function Page() {
  const [view, setView] = useState("landing");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [activeTemplateId, setActiveTemplateId] = useState<string | undefined>(undefined);
  const [traceToReplay, setTraceToReplay] = useState<TraceEvent | null>(null);
  const [win, setWin] = useState(3600);
  const [auto, setAuto] = useState(true);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [traces, setTraces] = useState<TraceEvent[]>([]);
  const [filters, setFilters] = useState<TraceFilters>({});
  const [selected, setSelected] = useState<TraceEvent | null>(null);
  const [evalRuns, setEvalRuns] = useState<EvalRun[]>([]);

  const refresh = useCallback(async () => {
    const [m, t] = await Promise.all([getMetrics(win), getTraces(filters, 100)]);
    setMetrics(m);
    setTraces(t);
  }, [win, filters]);

  // Load eval runs when switching to eval view
  useEffect(() => {
    if (view === "eval") {
      getEvalRuns().then(setEvalRuns);
    }
  }, [view]);

  useEffect(() => {
    if (view !== "landing") {
      refresh();
    }
  }, [refresh, view]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const tab = params.get("tab");
      if (tab && tab !== "landing") {
        setView(tab);
      } else {
        setView("landing");
      }

      const handlePopState = () => {
        const p = new URLSearchParams(window.location.search);
        const t = p.get("tab");
        setView(t && t !== "landing" ? t : "landing");
      };
      window.addEventListener("popstate", handlePopState);
      return () => window.removeEventListener("popstate", handlePopState);
    }
  }, []);

  const handleViewChange = (v: string) => {
    setView(v);
    setMobileNavOpen(false);
    if (typeof window !== "undefined") {
      if (v === "landing") {
        window.history.pushState(null, "", "/");
      } else {
        window.history.pushState(null, "", `?tab=${v}`);
      }
    }
  };

  if (view === "landing") {
    return <LandingPage onNavigate={handleViewChange} />;
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <TopBar
        window={win}
        onWindow={setWin}
        auto={auto}
        onAuto={() => setAuto((a) => !a)}
        live={isLive()}
        hideControls={view === "playground" || view === "canvas"}
        onHome={() => handleViewChange("landing")}
        onToggleMobileMenu={() => setMobileNavOpen((o) => !o)}
      />
      <div className="flex flex-1 min-h-0 overflow-hidden">
        <Sidebar view={view} onView={handleViewChange} />
        <main className={`flex-1 min-w-0 h-full ${view === "canvas" ? "p-0 overflow-hidden" : "p-3.5 sm:p-6 pb-20 md:pb-6 overflow-y-auto"}`}>
          {view === "canvas" && (
            <AgentCanvas
              initialTemplateId={activeTemplateId}
              initialTraceToReplay={traceToReplay}
              onNavigateToTracing={(traceId) => {
                handleViewChange("tracing");
              }}
            />
          )}
          {view === "workflows" && (
            <WorkflowsPanel
              onOpenCanvas={(templateId) => {
                setActiveTemplateId(templateId);
                handleViewChange("canvas");
              }}
              onNavigateToTracing={() => handleViewChange("tracing")}
            />
          )}
          {view === "tests" && (
            <TestSuitePanel
              onReplayTestCase={(tc) => {
                const trace: TraceEvent = {
                  id: tc.id,
                  ts: Math.floor(Date.now() / 1000),
                  op: "agent_eval",
                  namespace: "knowledge-base",
                  latency_ms: tc.durationMs || 142,
                  n_results: 5,
                  top_k: 5,
                  cache_hit: tc.name.includes("cache"),
                  filtered: false,
                  rescore: null,
                  rerank: "cross-encoder",
                  score_top: tc.faithfulness || 0.95,
                  score_mean: 0.90,
                  status: tc.status === "failed" ? "err" : "ok",
                  error: null,
                  query_preview: tc.query,
                };
                setTraceToReplay(trace);
                handleViewChange("canvas");
              }}
              onOpenCanvas={(templateId) => {
                setActiveTemplateId(templateId);
                handleViewChange("canvas");
              }}
            />
          )}
          {view === "tracing" && (
            <>
              {metrics && <Kpis m={metrics} />}
              {metrics && (
                <div className="grid grid-cols-1 lg:grid-cols-[1.5fr_1fr] gap-4 mb-5">
                  <VolumeChart m={metrics} />
                  <LatencyChart m={metrics} />
                </div>
              )}
              <TracesTable
                traces={traces}
                filters={filters}
                onFilter={setFilters}
                onSelect={async (id) => setSelected(await getTrace(id))}
              />
              <p className="font-mono text-[11.5px] text-faint mt-2">
                {isLive() ? "Live telemetry from a running dynavec client." : "Sample data — set NEXT_PUBLIC_DYNAVEC_API to a running dynavec.dashboard.serve() endpoint."}
              </p>
            </>
          )}
          {view === "playground" && <SearchPlayground />}
          {view === "latency" && <LatencyPanel m={metrics} traces={traces} />}
          {view === "cost" && <CostPanel />}
          {view === "eval" && <EvalTrends runs={evalRuns} />}
          {view === "faithfulness" && <FaithfulnessPanel />}
          {view === "resources" && <ResourcesPanel />}
          {view === "namespaces" && (
            <NamespacesPanel
              traces={traces}
              onSelectNamespace={(ns) => {
                setFilters({ ...filters, namespace: ns });
                setView("tracing");
              }}
            />
          )}
        </main>
      </div>
      <TraceDrawer
        trace={selected}
        onClose={() => setSelected(null)}
        onReplayTrace={(t) => {
          setSelected(null);
          setTraceToReplay(t);
          handleViewChange("canvas");
        }}
      />

      {/* ── Mobile Slide-Over Drawer ── */}
      {mobileNavOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex" role="dialog" aria-modal="true">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
            onClick={() => setMobileNavOpen(false)}
          />
          <div className="relative z-10 h-full shadow-2xl animate-in slide-in-from-left duration-200">
            <Sidebar
              view={view}
              onView={(v) => {
                handleViewChange(v);
                setMobileNavOpen(false);
              }}
              isMobileDrawer={true}
              onCloseMobile={() => setMobileNavOpen(false)}
            />
          </div>
        </div>
      )}

      {/* ── Mobile Bottom Navigation Bar (Quick Access) ── */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 h-14 bg-surface/95 backdrop-blur-lg border-t border-line z-40 flex items-center justify-around px-1.5 select-none shadow-lg"
        style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
      >
        <button
          type="button"
          onClick={() => handleViewChange("playground")}
          className={`flex flex-col items-center justify-center flex-1 py-1 transition-colors cursor-pointer ${
            view === "playground" ? "text-accent font-semibold" : "text-muted hover:text-ink"
          }`}
        >
          <svg className="w-5 h-5 mb-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <circle cx="11" cy="11" r="7" strokeWidth="1.8" />
            <path strokeWidth="1.8" strokeLinecap="round" d="m20 20-3.5-3.5" />
          </svg>
          <span className="text-[10px] tracking-tight">Query</span>
        </button>

        <button
          type="button"
          onClick={() => handleViewChange("canvas")}
          className={`flex flex-col items-center justify-center flex-1 py-1 transition-colors cursor-pointer ${
            view === "canvas" ? "text-accent font-semibold" : "text-muted hover:text-ink"
          }`}
        >
          <svg className="w-5 h-5 mb-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <rect x="3" y="3" width="7" height="7" rx="1.5" strokeWidth="1.8" />
            <rect x="14" y="3" width="7" height="7" rx="1.5" strokeWidth="1.8" />
            <rect x="14" y="14" width="7" height="7" rx="1.5" strokeWidth="1.8" />
            <path strokeWidth="1.8" strokeLinecap="round" d="M10 6.5h4M6.5 10v7.5a1.5 1.5 0 0 0 1.5 1.5H14" />
          </svg>
          <span className="text-[10px] tracking-tight">Canvas</span>
        </button>

        <button
          type="button"
          onClick={() => handleViewChange("workflows")}
          className={`flex flex-col items-center justify-center flex-1 py-1 transition-colors cursor-pointer ${
            view === "workflows" ? "text-accent font-semibold" : "text-muted hover:text-ink"
          }`}
        >
          <svg className="w-5 h-5 mb-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" d="M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6z" />
            <path strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" d="M14 10v4M10 14h8a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-2a2 2 0 0 1 2-2h4" />
          </svg>
          <span className="text-[10px] tracking-tight">Flows</span>
        </button>

        <button
          type="button"
          onClick={() => handleViewChange("tracing")}
          className={`flex flex-col items-center justify-center flex-1 py-1 transition-colors cursor-pointer ${
            view === "tracing" ? "text-accent font-semibold" : "text-muted hover:text-ink"
          }`}
        >
          <svg className="w-5 h-5 mb-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h10M4 18h14" />
            <circle cx="18" cy="12" r="2" strokeWidth="1.8" />
          </svg>
          <span className="text-[10px] tracking-tight">Traces</span>
        </button>

        <button
          type="button"
          onClick={() => setMobileNavOpen(true)}
          className="flex flex-col items-center justify-center flex-1 py-1 text-muted hover:text-ink transition-colors cursor-pointer"
        >
          <svg className="w-5 h-5 mb-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <circle cx="5" cy="12" r="1.5" strokeWidth="1.8" />
            <circle cx="12" cy="12" r="1.5" strokeWidth="1.8" />
            <circle cx="19" cy="12" r="1.5" strokeWidth="1.8" />
          </svg>
          <span className="text-[10px] tracking-tight">More</span>
        </button>
      </nav>
    </div>
  );
}
