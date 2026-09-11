# Dynavec Production Operations Runbook

This runbook documents the deployment, continuous monitoring, security practices, and lifecycle management for Dynavec.

---

## 1. Live Environment Overview

* **AWS Region**: `us-east-1` (N. Virginia)
* **AWS Account ID**: `212919533030`
* **DynamoDB Document Table**: `dynavec_docs` (Mode: `PAY_PER_REQUEST` / Auto-scaling)
* **S3 Vector Bucket**: `dynavec-vectors-212919533030` (AES-256 Server-Side Encryption)
* **S3 Vectors Index**: `docs-index` (Metric: Cosine Similarity)
* **Observability Dashboard**: [http://localhost:3000](http://localhost:3000)
* **Local Telemetry API**: [http://127.0.0.1:8779](http://127.0.0.1:8779)
* **Landing Page**: [http://127.0.0.1:8777](http://127.0.0.1:8777)

---

## 2. Production Multi-Tenant Architecture

Dynavec enforces strict multi-tenant hardware boundaries at the database level:
* **Composite Primary Key**: `pk = "{namespace}#{document_id}"`
* **Active Verified Namespaces**:
  * `production-core`: Core enterprise knowledge base (Cloud Architecture, AI/RAG Systems, DevOps CI/CD).
  * `live-demo`: Continuous latency verification documents.
* **Semantic Cache**: Warm queries are answered in `< 0.3 ms` directly from local RAM with zero AWS network cost.

---

## 3. Production Smoke Testing

To verify end-to-end cloud connectivity, dual-write consistency, and cache hits at any time:

```powershell
.\.venv\Scripts\python.exe scripts\production_smoke_test.py
```

Expected Output:
```
CHECK                                  | STATUS   | LATENCY / DETAILS
Dual-Write Ingestion (DynamoDB + S3)   | [PASS]   | ~1900 ms
Cold AWS Cloud Search                  | [PASS]   | ~730 ms (found: True)
Warm Semantic Cache Hit                | [PASS]   | 0.24 ms
>>> ALL PRODUCTION INVARIANTS VERIFIED SUCCESSFULLY! <<<
```

---

## 4. Production Embedding Model Switcher

| Provider | Model | Dimension | Configuration in `.env` |
| :--- | :--- | :--- | :--- |
| **Local Zero-Cost (Current)** | `LocalDeterministicEmbedder` | 16 | Used for ₹0 local development and testing |
| **AWS Bedrock Titan (AWS Native)** | `amazon.titan-embed-text-v2:0` | 1024 or 1536 | Set `DYNAVEC_EMBEDDER=bedrock` |
| **OpenAI** | `text-embedding-3-small` | 1536 | Set `OPENAI_API_KEY=sk-...` |

---

## 5. Container Deployment (Docker & ECS)

Build and run the unified production container (Next.js Dashboard + Python Telemetry API):

```powershell
# Using Docker Compose
docker compose up -d

# Or build manually
docker build -t dynavec-service:latest .
docker run -p 8779:8779 -p 3000:3000 --env-file .env dynavec-service:latest
```

---

## 6. Day-2 Clean Teardown Procedure

When your 2-day testing window is complete, destroy all cloud resources to ensure **₹0 ongoing cost**:

```powershell
cd g:\vectore_db_contribution\dynavec\deploy\terraform
terraform destroy -auto-approve
```

This will cleanly delete:
1. DynamoDB Table: `dynavec_docs`
2. S3 Vector Bucket: `dynavec-vectors-212919533030` (with `force_destroy = true`)
3. S3 Vectors Index: `docs-index`
