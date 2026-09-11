import type { EvalRun, Metrics, TraceEvent, TraceFilters } from "./types";
import { mockMetrics, mockTraces } from "./mock";

// Point this at a running `dynavec.dashboard.serve(recorder)` API.
const API_BASE = process.env.NEXT_PUBLIC_DYNAVEC_API || "http://127.0.0.1:8779";

let _mockTraces: TraceEvent[] | null = null;
function sampleTraces(): TraceEvent[] {
  if (!_mockTraces) _mockTraces = mockTraces(60);
  return _mockTraces;
}

export function isLive(): boolean {
  return Boolean(API_BASE);
}

export async function getMetrics(windowSeconds: number): Promise<Metrics> {
  if (API_BASE) {
    try {
      const r = await fetch(`${API_BASE}/api/metrics?window=${windowSeconds}`, { cache: "no-store" });
      if (r.ok) return (await r.json()) as Metrics;
    } catch { /* fall through to sample */ }
  }
  return mockMetrics(sampleTraces());
}

export async function getTraces(filters: TraceFilters, limit = 100): Promise<TraceEvent[]> {
  if (API_BASE) {
    try {
      const q = new URLSearchParams({ limit: String(limit) });
      if (filters.op) q.set("op", filters.op);
      if (filters.status) q.set("status", filters.status);
      if (filters.namespace) q.set("namespace", filters.namespace);
      const r = await fetch(`${API_BASE}/api/traces?${q}`, { cache: "no-store" });
      if (r.ok) return (await r.json()) as TraceEvent[];
    } catch { /* fall through */ }
  }
  return sampleTraces().filter((e) =>
    (!filters.op || e.op === filters.op) &&
    (!filters.status || e.status === filters.status) &&
    (!filters.namespace || e.namespace.includes(filters.namespace)),
  );
}

export async function getTrace(id: string): Promise<TraceEvent | null> {
  if (API_BASE) {
    try {
      const r = await fetch(`${API_BASE}/api/trace/${id}`, { cache: "no-store" });
      if (r.ok) return (await r.json()) as TraceEvent;
    } catch { /* fall through */ }
  }
  return sampleTraces().find((e) => e.id === id) || null;
}

/** Generate sample eval runs for dev/preview mode. */
function mockEvalRuns(): EvalRun[] {
  const now = Date.now() / 1000;
  const days = 8;
  return Array.from({ length: days }, (_, i) => {
    const progress = (i + 1) / days;  // 0.125 → 1.0
    return {
      dataset: "qa-benchmark",
      ks: [1, 5, 10, 20],
      n_queries: 50,
      mrr: 0.35 + progress * 0.35,
      recall: {
        "1": 0.20 + progress * 0.30,
        "5": 0.45 + progress * 0.30,
        "10": 0.60 + progress * 0.25,
        "20": 0.75 + progress * 0.18,
      },
      ndcg: {
        "1": 0.20 + progress * 0.30,
        "5": 0.40 + progress * 0.32,
        "10": 0.55 + progress * 0.28,
        "20": 0.68 + progress * 0.22,
      },
      timestamp: now - (days - i) * 86400,
    };
  });
}

export async function getEvalRuns(): Promise<EvalRun[]> {
  if (API_BASE) {
    try {
      const r = await fetch(`${API_BASE}/api/eval`, { cache: "no-store" });
      if (r.ok) return (await r.json()) as EvalRun[];
    } catch { /* fall through to sample */ }
  }
  return mockEvalRuns();
}

export interface SearchItem {
  id: string;
  text: string;
  score: number;
  metadata?: Record<string, any>;
}

export interface SearchResponse {
  query: string;
  namespace: string;
  latency_ms: number;
  results: SearchItem[];
}

export async function searchKnowledgeBase(
  query: string,
  namespace = "production-core",
  top_k = 3
): Promise<SearchResponse> {
  const q = new URLSearchParams({ q: query, namespace, top_k: String(top_k) });
  const r = await fetch(`${API_BASE}/api/search?${q}`, { cache: "no-store" });
  if (!r.ok) {
    throw new Error(`Search failed: ${r.statusText}`);
  }
  return (await r.json()) as SearchResponse;
}

export async function upsertDocument(
  text: string,
  namespace = "production-core",
  id?: string,
  metadata?: Record<string, any>
): Promise<{ status: string; id: string; namespace: string; latency_ms: number }> {
  const r = await fetch(`${API_BASE}/api/upsert`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, namespace, id, metadata }),
  });
  if (!r.ok) {
    throw new Error(`Upsert failed: ${r.statusText}`);
  }
  return await r.json();
}

export async function getNamespacesList(): Promise<string[]> {
  try {
    const r = await fetch(`${API_BASE}/api/namespaces`, { cache: "no-store" });
    if (r.ok) return (await r.json()) as string[];
  } catch { /* ignore */ }
  return ["production-core", "live-demo"];
}
