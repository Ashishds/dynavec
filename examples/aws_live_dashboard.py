"""Run Dynavec Dashboard connected 100% to REAL AWS Cloud (DynamoDB & S3).

Every trace in the dashboard will be a physical network call to Amazon DynamoDB
and Amazon S3 Vectors in AWS us-east-1.
"""

from __future__ import annotations

import math
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

os.environ.pop("DYNAVEC_DASHBOARD_TOKEN", None)

from dynavec import Document, Dynavec, DynavecConfig, SemanticCache
from dynavec.dashboard import serve
from dynavec.embeddings.base import Embedder
from dynavec.telemetry import TelemetryRecorder

DIM = 16


class LocalDeterministicEmbedder(Embedder):
    def __init__(self, dimension: int = DIM) -> None:
        self.dimension = dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        import hashlib
        import re
        out = []
        for t in texts:
            v = [0.0] * self.dimension
            words = re.findall(r"\w+", t.lower())
            for w in words:
                h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
                idx = h % self.dimension
                sign = 1.0 if ((h >> 8) & 1) else -1.0
                v[idx] += sign
            norm = math.sqrt(sum(x * x for x in v)) or 1e-9
            out.append([x / norm for x in v])
        return out


def main() -> None:
    region = os.environ.get("AWS_REGION", "us-east-1")
    bucket = os.environ.get("DYNAVEC_VECTOR_BUCKET", "dynavec-vectors-212919533030")
    table = os.environ.get("DYNAVEC_TABLE", "dynavec_docs")
    index = os.environ.get("DYNAVEC_INDEX", "docs-index")

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

    # Real AWS Dynavec client - NO MOCKS, NO FAKE STORES!
    db = Dynavec(
        cfg,
        embedder=LocalDeterministicEmbedder(DIM),
        cache=SemanticCache(threshold=0.9),
        telemetry=rec,
    )

    print("==========================================================")
    print(" Dynavec Dashboard: 100% REAL AWS CLOUD CONNECTED ")
    print(f" DynamoDB Table: {table}")
    print(f" S3 Vector Bucket: {bucket}")
    print("==========================================================")

    # Seed initial real AWS searches
    queries = [
        ("serverless cloud database latency", "live-demo"),
        ("dynamodb fast document hydration", "production-core"),
        ("retrieval augmented generation rag", "production-core"),
        ("vector memory compression accuracy", "production-core"),
        ("terraform automated infrastructure provisioning", "production-core"),
        ("s3 vectors ann indexing", "live-demo"),
    ]

    for q, ns in queries:
        try:
            db.search(q, top_k=2, namespace=ns)
        except Exception as e:
            print("Search notice:", e)

    def live_workload():
        while True:
            time.sleep(random.uniform(4.0, 8.0))
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
    serve(rec, port=8779, eval_dir=evals_dir, db=db)


if __name__ == "__main__":
    main()
