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

export default function Page() {
  const [view, setView] = useState("tracing");
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

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    if (!auto) return;
    const id = setInterval(refresh, 4000);
    return () => clearInterval(id);
  }, [auto, refresh]);

  return (
    <>
      <TopBar window={win} onWindow={setWin} auto={auto} onAuto={() => setAuto((a) => !a)} live={isLive()} />
      <div className="flex min-h-[calc(100vh-52px)]">
        <Sidebar view={view} onView={setView} />
        <main className="flex-1 min-w-0 p-6">
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
      <TraceDrawer trace={selected} onClose={() => setSelected(null)} />
    </>
  );
}
