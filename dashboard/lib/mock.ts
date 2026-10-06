import type { Metrics, TraceEvent } from "./types";

// Deterministic-ish sample data so the dashboard renders standalone (dev, static
// export, first run) before it is pointed at a live dynavec telemetry API.
const NS = [
  "production-core",
  "production-core",
  "transformer-paper",
  "portfolio-demo",
  "live-demo",
];
const OPS = ["search", "search", "search", "graph_search", "upsert"];
const RANK = [null, null, "cosine", "mmr", "dot"];

let seed = 42;
function rand() {
  seed = (seed * 1103515245 + 12345) & 0x7fffffff;
  return seed / 0x7fffffff;
}
function pick<T>(a: T[]): T {
  return a[Math.floor(rand() * a.length)];
}

export function mockTraces(n = 60): TraceEvent[] {
  const now = Date.now() / 1000;
  const out: TraceEvent[] = [];
  for (let i = 0; i < n; i++) {
    const op = pick(OPS);
    const namespace = pick(NS);
    const cacheHit = op === "upsert" ? null : rand() > 0.65; // ~35% cache hits
    const nres = op === "upsert" ? 0 : pick([3, 5, 5, 10]);

    let embed_ms = 0;
    let ann_ms = 0;
    let hydrate_ms = 0;
    let rerank_ms = 0;
    let lat = 0;

    if (op === "upsert") {
      embed_ms = Math.round((2.0 + rand() * 1.5) * 10) / 10;
      ann_ms = Math.round((12.0 + rand() * 8.0) * 10) / 10;
      hydrate_ms = Math.round((5.0 + rand() * 4.0) * 10) / 10;
      rerank_ms = 0;
      lat = Math.round((embed_ms + ann_ms + hydrate_ms) * 10) / 10;
    } else if (cacheHit) {
      // Sub-millisecond ANN cache lookup + single-digit hydration
      embed_ms = Math.round((1.0 + rand() * 0.6) * 10) / 10;
      ann_ms = 0;
      hydrate_ms = Math.round((2.5 + rand() * 1.8) * 10) / 10;
      rerank_ms = Math.round((0.3 + rand() * 0.3) * 100) / 100;
      lat = Math.round((embed_ms + ann_ms + hydrate_ms + rerank_ms) * 10) / 10;
    } else {
      // Standard in-account AWS query roundtrip:
      // S3 Vectors ANN (~14-25ms) + DynamoDB BatchGetItem (~3-7ms) + Dense Embed (~1.5-2.5ms) + Rerank (~0.8-1.6ms)
      const isTailCold = rand() > 0.94; // 6% tail cold latency
      embed_ms = Math.round((1.5 + rand() * 1.2) * 10) / 10;
      ann_ms = isTailCold
        ? Math.round((42.0 + rand() * 30.0) * 10) / 10
        : Math.round((14.0 + rand() * 11.0) * 10) / 10;
      hydrate_ms = isTailCold
        ? Math.round((10.0 + rand() * 8.0) * 10) / 10
        : Math.round((3.8 + rand() * 3.2) * 10) / 10;
      rerank_ms = op === "graph_search"
        ? Math.round((1.5 + rand() * 1.2) * 10) / 10
        : Math.round((0.8 + rand() * 0.8) * 10) / 10;
      lat = Math.round((embed_ms + ann_ms + hydrate_ms + rerank_ms) * 10) / 10;
    }

    out.push({
      id: Math.random().toString(16).slice(2, 14),
      ts: now - i * 3,
      op,
      namespace,
      latency_ms: lat,
      n_results: nres,
      top_k: op === "upsert" ? null : nres,
      cache_hit: cacheHit,
      filtered: rand() > 0.6,
      rescore: op === "search" ? pick(RANK) : null,
      rerank: rand() > 0.7 ? "hybrid" : null,
      score_top: op === "upsert" ? null : Math.round((0.78 + rand() * 0.20) * 1000) / 1000,
      score_mean: op === "upsert" ? null : Math.round((0.68 + rand() * 0.18) * 1000) / 1000,
      status: rand() > 0.98 ? "error" : "ok",
      error: null,
      query_preview:
        op === "upsert"
          ? null
          : namespace === "transformer-paper"
          ? pick([
              "scaled dot-product attention formula",
              "multi-head attention projection",
              "positional encoding sinusoidal",
              "computational complexity self-attention",
            ])
          : pick([
              "DynamoDB single-digit ms hydration",
              "S3 Vectors serverless index pricing",
              "hybrid retrieval BM25 cosine",
              "vector memory compression Matryoshka",
            ]),
      embed_ms,
      ann_ms,
      hydrate_ms,
      rerank_ms,
    });
  }
  return out;
}

export function mockMetrics(traces: TraceEvent[]): Metrics {
  const win = traces;
  const lat = win
    .filter((e) => e.status === "ok")
    .map((e) => e.latency_ms)
    .sort((a, b) => a - b);
  const pct = (p: number) =>
    lat.length ? lat[Math.min(lat.length - 1, Math.floor((lat.length - 1) * p))] : 0;
  const cacheScoped = win.filter((e) => e.cache_hit !== null);
  const hits = cacheScoped.filter((e) => e.cache_hit).length;
  const buckets = 30;
  const hist = new Array(buckets).fill(0);
  win.forEach((_, i) => {
    hist[Math.min(buckets - 1, Math.floor((i / win.length) * buckets))]++;
  });
  const op_mix: Record<string, number> = {};
  win.forEach((e) => {
    op_mix[e.op] = (op_mix[e.op] || 0) + 1;
  });
  const namespaces: Record<string, number> = {};
  win.forEach((e) => {
    namespaces[e.namespace] = (namespaces[e.namespace] || 0) + 1;
  });

  return {
    total: win.length,
    qpm: Math.round((win.length / 60) * 100) / 100 * 6,
    p50: Math.round(pct(0.5) * 10) / 10,
    p95: Math.round(pct(0.95) * 10) / 10,
    p99: Math.round(pct(0.99) * 10) / 10,
    cache_hit_rate: cacheScoped.length
      ? Math.round((1000 * hits) / cacheScoped.length) / 10
      : null,
    cache_hits: hits,
    cache_total: cacheScoped.length,
    error_rate:
      Math.round(
        (1000 * win.filter((e) => e.status === "error").length) /
          Math.max(1, win.length)
      ) / 10,
    avg_results:
      Math.round(
        (10 * win.reduce((s, e) => s + e.n_results, 0)) / Math.max(1, win.length)
      ) / 10,
    op_mix,
    namespaces,
    histogram: hist,
    bucket_width_s: 120,
    window_start: 0,
    window_seconds: 3600,
  };
}
