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
      if (r.ok) {
        const data = (await r.json()) as EvalRun[];
        if (data && data.length > 0) return data;
      }
    } catch { /* fall through to sample */ }
  }
  return mockEvalRuns();
}

export interface LatencyBreakdown {
  embed_ms: number;
  ann_ms: number;
  hydrate_ms: number;
  rerank_ms: number;
  llm_ms: number;
  total_ms: number;
}

export interface Citation {
  index: number;
  id: string;
  filename?: string;
  page?: number | string;
  snippet: string;
  score?: number;
}

export interface SynthesizedAnswer {
  query: string;
  text: string;
  citations: Citation[];
  model: string;
  latency_ms: number;
  confidence?: "high" | "medium" | "low";
  confidence_score?: number;
  confidence_reason?: string;
  is_low_confidence?: boolean;
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
  breakdown?: LatencyBreakdown;
  rerank_applied?: string;
  candidates_count?: number;
  confidence?: "high" | "medium" | "low";
  confidence_score?: number;
  confidence_reason?: string;
  is_low_confidence?: boolean;
  synthesis?: SynthesizedAnswer;
  results: SearchItem[];
  query_terms?: string[];
}

export async function searchKnowledgeBase(
  query: string,
  namespace = "production-core",
  top_k = 3,
  rerank = "hybrid",
  candidate_k = 20,
  synthesize = true
): Promise<SearchResponse> {
  const q = new URLSearchParams({
    q: query,
    namespace,
    top_k: String(top_k),
    rerank,
    candidate_k: String(candidate_k),
    synthesize: String(synthesize),
  });
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

export interface NamespaceItemStat {
  name: string;
  count: number;
  status: string;
  pkPattern: string;
  env: string;
}

export interface NamespaceStatsResponse {
  total_items: number;
  table: string;
  region: string;
  namespaces: NamespaceItemStat[];
}

export async function getNamespaceStats(): Promise<NamespaceStatsResponse | null> {
  try {
    const r = await fetch(`${API_BASE}/api/namespaces/stats`, { cache: "no-store" });
    if (r.ok) return (await r.json()) as NamespaceStatsResponse;
  } catch { /* ignore */ }
  return null;
}

export interface ResourceStatusResponse {
  account_id: string;
  region: string;
  dynamodb: {
    name: string;
    arn: string;
    status: string;
    billing: string;
    key_schema: string;
    item_count: number;
    size_bytes: number;
    creation_date: string;
  };
  s3_bucket: {
    name: string;
    arn: string;
    status: string;
    encryption: string;
  };
  s3_index: {
    name: string;
    arn: string;
    status: string;
    dimensions: number;
    metric: string;
  };
}

export async function getResourceStatus(): Promise<ResourceStatusResponse | null> {
  try {
    const r = await fetch(`${API_BASE}/api/resources/status`, { cache: "no-store" });
    if (r.ok) return (await r.json()) as ResourceStatusResponse;
  } catch { /* ignore */ }
  return null;
}

export async function getWorkloadStatus(): Promise<boolean> {
  try {
    const r = await fetch(`${API_BASE}/api/workload/status`, { cache: "no-store" });
    if (r.ok) {
      const data = await r.json();
      return Boolean(data.enabled);
    }
  } catch { /* ignore */ }
  return false;
}

export async function toggleWorkload(): Promise<boolean> {
  try {
    const r = await fetch(`${API_BASE}/api/workload/toggle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (r.ok) {
      const data = await r.json();
      return Boolean(data.enabled);
    }
  } catch { /* ignore */ }
  return false;
}

export interface AuditEvaluationResponse {
  question: string;
  faithfulness: number;
  relevance: number;
  context_relevance?: number;
  reason: string;
  overall_score?: number;
  verdict: string;
  model: string;
  details?: any;
}

export async function auditEvaluation(
  question: string,
  answer: string,
  context: string
): Promise<AuditEvaluationResponse> {
  const r = await fetch(`${API_BASE}/api/eval/audit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, answer, context }),
  });
  if (!r.ok) {
    throw new Error(`Audit request failed: ${r.statusText}`);
  }
  return (await r.json()) as AuditEvaluationResponse;
}
export interface BatchTestResult {
  query: string;
  confidence: "high" | "medium" | "low" | "error";
  confidence_score: number;
  is_low_confidence: boolean;
  latency_ms: number;
  n_results: number;
  top_result: {
    id: string;
    score: number;
    text: string;
    metadata?: Record<string, any>;
  } | null;
  status: "ok" | "error";
  error?: string;
}

export interface BatchTestResponse {
  total_queries: number;
  total_latency_ms: number;
  avg_latency_ms: number;
  avg_confidence_score: number;
  guardrail_triggered: number;
  results: BatchTestResult[];
}

export async function batchTest(
  queries: string[],
  namespace = "production-core",
  top_k = 3,
  candidate_k = 20,
  rerank = "hybrid"
): Promise<BatchTestResponse> {
  const r = await fetch(`${API_BASE}/api/batch-test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ queries, namespace, top_k, candidate_k, rerank }),
  });
  if (!r.ok) {
    throw new Error(`Batch test failed: ${r.statusText}`);
  }
  return (await r.json()) as BatchTestResponse;
}
