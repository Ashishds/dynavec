# Dynavec Observability Dashboard

Dynavec comes with a built-in, production-ready observability dashboard for real-time telemetry, latency profiling, request tracing, and offline retrieval quality tracking.

All numbers in the dashboard represent **real operation telemetry** captured directly from client requests — no simulations or synthetic filler.

![Dynavec Dashboard](assets/dashboard.png)

---

## Features

- **Real-Time KPI Cards**: Total operations, queries per minute (QPM), p95 latency, and cache hit rates.
- **Latency Distribution & Breakdown**:
  - Percentiles: p50, p95, p99
  - Phase breakdown: Embedding generation, ANN vector search, DynamoDB hydration, and reranking.
- **Traces Table & Event Drawer**:
  - Searchable, filterable log of operations (`search`, `upsert`, `graph_search`).
  - Detailed side drawer showing per-query parameters, latency phases, and score distributions.
- **Retrieval Quality Trends (Eval Panel)**:
  - Track offline evaluation metrics across versions and runs.
  - Interactive line charts for **Recall@k**, **nDCG@k**, and **MRR**.
- **Dark Mode Support**:
  - Seamless light and dark themes matching the Dynavec brand palette.
  - Persistent preference stored in `localStorage` with system default fallback.
- **Security by Default**:
  - Localhost binding (`127.0.0.1`) by default.
  - Optional Bearer token authentication via `DYNAVEC_DASHBOARD_TOKEN`.
  - Security headers including `X-Content-Type-Options: nosniff`.
  - Zero browser leakage of AWS credentials.

---

## Quick Start

### 1. Enable Telemetry in Python

Attach a `TelemetryRecorder` when creating your Dynavec client:

```python
from dynavec import Dynavec, DynavecConfig
from dynavec.telemetry import TelemetryRecorder
from dynavec.dashboard import serve

# Initialize recorder
recorder = TelemetryRecorder(max_events=10_000, capture_text=False)

# Pass recorder to your client
cfg = DynavecConfig(
    vector_bucket="my-vectors",
    index="docs",
    table="dynavec_docs",
    dimension=1536,
)
db = Dynavec(cfg, telemetry=recorder)

# Ingest and query
db.upsert([{"id": "doc1", "text": "Serverless vector search on S3 and DynamoDB"}])
results = db.search("serverless vector db", top_k=5)

# Start dashboard server (blocking)
serve(recorder, port=8778, host="127.0.0.1")
```

Open your browser at `http://127.0.0.1:8778`.

---

## CLI Usage

You can also run the dashboard via the `dynavec` CLI:

```bash
# Start on default localhost:8778
dynavec dashboard

# Custom port and binding
dynavec dashboard --port 8778 --host 127.0.0.1

# With eval results directory for retrieval quality trends
dynavec dashboard --eval-dir ./eval_results

# With token security
dynavec dashboard --token "my-secret-key"
```

### CLI Arguments

| Argument | Description | Default |
|:---|:---|:---|
| `--port` | Port for the dashboard HTTP server | `8778` |
| `--host` | Host address to bind to | `127.0.0.1` |
| `--eval-dir` | Path to directory with `eval-*.json` files | `None` |
| `--token` | Token for Bearer auth (or set `DYNAVEC_DASHBOARD_TOKEN`) | `None` |

---

## Security Configuration

When deploying the dashboard or running in shared environments:

1. **Set Authentication Token**:
   ```bash
   export DYNAVEC_DASHBOARD_TOKEN="your-secure-token-here"
   dynavec dashboard
   ```
   All requests must provide:
   ```http
   Authorization: Bearer your-secure-token-here
   ```

2. **Network Isolation**:
   By default, the dashboard binds to `127.0.0.1` preventing external network access. If binding to `0.0.0.0`, ensure you place it behind a reverse proxy (e.g. Nginx, Cloudflare Access) with HTTPS and authentication.

---

## Retrieval Quality Tracking

Dynavec's offline evaluation runner (`dynavec.eval`) writes benchmark results in JSON format:

```python
from dynavec.eval import EvalDataset, run_eval

dataset = EvalDataset.from_json("eval_dataset.json")
result = run_eval(db, dataset, ks=[1, 5, 10, 20])
result.to_json("eval_results/eval-run-001.json")
```

When you pass `--eval-dir ./eval_results` to `dynavec dashboard`:
- The `/api/eval` endpoint loads all `eval-*.json` runs.
- Navigate to the **"Scores"** panel in the dashboard sidebar to view historical Recall, MRR, and nDCG curves.

---

## Running the Next.js Frontend Directly

For development or hosting the frontend as a standalone web application:

```bash
cd dashboard
npm install
npm run dev
```

To build for production:

```bash
cd dashboard
npm run build
npm start
```
