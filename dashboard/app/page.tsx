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
    <>
      <TopBar
        window={win}
        onWindow={setWin}
        auto={auto}
        onAuto={() => setAuto((a) => !a)}
        live={isLive()}
        hideControls={view === "playground" || view === "canvas"}
        onHome={() => handleViewChange("landing")}
      />
      <div className="flex min-h-[calc(100vh-52px)]">
        <Sidebar view={view} onView={handleViewChange} />
        <main className={`flex-1 min-w-0 ${view === "canvas" ? "p-0" : "p-6"}`}>
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
    </>
  );
}
