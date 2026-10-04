"""Run Dynavec Dashboard connected 100% to REAL AWS Cloud (DynamoDB & S3).

Every trace in the dashboard will be a physical network call to Amazon DynamoDB
and Amazon S3 Vectors in AWS us-east-1.
"""

from __future__ import annotations

import os
import random
import threading
import time
from pathlib import Path

# Load .env
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if v.strip():
                os.environ.setdefault(k.strip(), v.strip())

# DEV MODE: Disable dashboard auth token so local browser can connect without headers.
# In production (DYNAVEC_PROD=true), always enforce the token if set in .env.
_PROD_MODE = os.environ.get("DYNAVEC_PROD", "false").lower() == "true"
if not _PROD_MODE:
    os.environ.pop("DYNAVEC_DASHBOARD_TOKEN", None)
else:
    # In prod mode, ensure a token is set — fail fast if not configured
    if not os.environ.get("DYNAVEC_DASHBOARD_TOKEN"):
        raise RuntimeError(
            "DYNAVEC_PROD=true but DYNAVEC_DASHBOARD_TOKEN is not set. "
            "Set a secure token in .env before running in production mode."
        )

from dynavec import Dynavec, DynavecConfig, SemanticCache
from dynavec.dashboard import serve
from dynavec.embeddings.openai import OpenAIEmbedder
from dynavec.embeddings.sentence_transformers import SentenceTransformerEmbedder
from dynavec.telemetry import TelemetryRecorder

# ── Embedder configuration ────────────────────────────────────────────────────
# Enterprise standard: OpenAI text-embedding-3-small with 384-dim Matryoshka shortening.
# Matches S3 Vectors index (384-dim) while delivering high MTEB semantic retrieval.
DEFAULT_OPENAI_MODEL = "text-embedding-3-small"
DEFAULT_ST_MODEL = "all-MiniLM-L6-v2"
DIM = 384  # Must match the S3 Vectors index dimension


def main() -> None:
    region = os.environ.get("AWS_REGION", "us-east-1")
    bucket = os.environ.get("DYNAVEC_VECTOR_BUCKET", "dynavec-vectors-212919533030")
    table = os.environ.get("DYNAVEC_TABLE", "dynavec_docs")
    index = os.environ.get("DYNAVEC_INDEX", "docs-index")

    # ── Semantic Embedder Selection ───────────────────────────────────────────
    # If OPENAI_API_KEY is configured, use the enterprise OpenAI embedder.
    # Otherwise, fall back to local sentence-transformers.
    if os.environ.get("OPENAI_API_KEY"):
        embedder_name = os.environ.get("OPENAI_EMBEDDING_MODEL", DEFAULT_OPENAI_MODEL)
        print(f"  Loading Enterprise OpenAI embedder: {embedder_name} ({DIM}-dim Matryoshka) ...")
        embedder = OpenAIEmbedder(model=embedder_name, dimension=DIM)
    else:
        print(f"  Loading SentenceTransformer embedder: {DEFAULT_ST_MODEL} ({DIM}-dim) ...")
        embedder = SentenceTransformerEmbedder(model=DEFAULT_ST_MODEL)
    print(f"  Embedder ready: {getattr(embedder, 'model', DEFAULT_ST_MODEL)} (dimension: {embedder.dimension})")

    rec = TelemetryRecorder(capture_text=True)
    cfg = DynavecConfig(
        vector_bucket=bucket,
        index=index,
        table=table,
        dimension=DIM,
        distance_metric="cosine",
        region=region,
        auto_provision=False,
    )

    # Real AWS Dynavec client — NO MOCKS, NO FAKE STORES!
    db = Dynavec(
        cfg,
        embedder=embedder,
        cache=SemanticCache(threshold=0.9),
        telemetry=rec,
    )

    print("==========================================================")
    print(" Dynavec Dashboard: 100% REAL AWS CLOUD CONNECTED ")
    print(f" DynamoDB Table: {table}")
    print(f" S3 Vector Bucket: {bucket}")
    print("==========================================================")

    # Workload controller (disabled by default so dashboard displays 100% real human queries)
    workload_controller = {"enabled": False}

    queries = [
        ("serverless cloud database latency", "live-demo"),
        ("dynamodb fast document hydration", "production-core"),
        ("retrieval augmented generation rag", "production-core"),
        ("vector memory compression accuracy", "production-core"),
        ("terraform automated infrastructure provisioning", "production-core"),
        ("s3 vectors ann indexing", "live-demo"),
    ]

    def live_workload():
        while True:
            time.sleep(random.uniform(4.0, 8.0))
            if not workload_controller.get("enabled", False):
                continue
            try:
                q, ns = random.choice(queries)
                db.search(
                    q,
                    top_k=random.choice([2, 3]),
                    namespace=ns,
                )
            except Exception:
                pass

    evals_dir = str(Path(__file__).resolve().parent.parent / "evals")
    threading.Thread(target=live_workload, daemon=True).start()
    serve(rec, port=8779, eval_dir=evals_dir, db=db, workload_controller=workload_controller)


if __name__ == "__main__":
    main()
