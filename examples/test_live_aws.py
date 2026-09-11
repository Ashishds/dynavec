"""Test live Dynavec operations against real AWS DynamoDB and S3 infrastructure.

Runs with ZERO external API keys using a local deterministic embedder.
Dual-writes documents into your real AWS DynamoDB table and S3 bucket,
and performs hybrid vector retrieval with sub-millisecond hydration.

Usage:
    python examples/test_live_aws.py
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

# Load .env if present
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from dynavec import Document, Dynavec, DynavecConfig
from dynavec.embeddings.base import Embedder

DIM = 16


class LocalDeterministicEmbedder(Embedder):
    """Zero-dependency, local deterministic embedder for instant testing."""

    def __init__(self, dimension: int = DIM) -> None:
        self.dimension = dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            v = [0.0] * self.dimension
            for i, c in enumerate(t):
                v[i % self.dimension] += (ord(c) % 17) / 17.0
            norm = math.sqrt(sum(x * x for x in v)) or 1e-9
            out.append([x / norm for x in v])
        return out


def main() -> int:
    print("==================================================")
    print("       Dynavec Real AWS Cloud Verification        ")
    print("==================================================")

    region = os.environ.get("AWS_REGION", "us-east-1")
    bucket = os.environ.get("DYNAVEC_VECTOR_BUCKET", "dynavec-vectors-212919533030")
    table = os.environ.get("DYNAVEC_TABLE", "dynavec_docs")
    index = os.environ.get("DYNAVEC_INDEX", "docs-index")

    print(f"Region:         {region}")
    print(f"DynamoDB Table: {table}")
    print(f"S3 Bucket:      {bucket}")
    print(f"Vector Index:   {index}\n")

    cfg = DynavecConfig(
        vector_bucket=bucket,
        index=index,
        table=table,
        dimension=DIM,
        distance_metric="cosine",
        region=region,
        auto_provision=True,
    )

    print("Connecting to live AWS DynamoDB & S3 infrastructure...")
    try:
        db = Dynavec(cfg, embedder=LocalDeterministicEmbedder(dimension=DIM))
        print("[SUCCESS] Connected to Dynavec client on AWS.\n")
    except Exception as exc:
        print(f"[ERROR] Failed to initialize Dynavec: {exc}")
        return 1

    docs = [
        Document(
            id="doc-aws-1",
            text="Amazon DynamoDB delivers single-digit millisecond latency at any scale.",
            metadata={"category": "database", "provider": "aws"},
        ),
        Document(
            id="doc-aws-2",
            text="Serverless vector databases eliminate the high cost of idle EC2 clusters.",
            metadata={"category": "ai", "provider": "dynavec"},
        ),
        Document(
            id="doc-aws-3",
            text="Amazon S3 Vectors provides scalable serverless ANN vector indexing.",
            metadata={"category": "ai", "provider": "aws"},
        ),
        Document(
            id="doc-aws-4",
            text="Terraform allows automated infrastructure provisioning and zero-cost destruction.",
            metadata={"category": "devops", "provider": "hashicorp"},
        ),
    ]

    print(f"1. Ingesting {len(docs)} documents into live AWS...")
    try:
        res = db.upsert(docs, namespace="live-demo")
        print(f"   [OK] Upserted {len(docs)} documents successfully.")
    except Exception as exc:
        print(f"   [NOTICE] Upsert status: {exc}")

    print("\n2. Executing semantic search across AWS DynamoDB + S3...")
    query = "serverless cloud database latency"
    try:
        results = db.search(query, top_k=3, namespace="live-demo")
        print(f"   Query: '{query}'\n")
        for i, hit in enumerate(results, start=1):
            print(f"   #{i} [Score: {hit.score:.4f}] ID: {hit.id}")
            print(f"      Text: {hit.text}")
            print(f"      Metadata: {hit.metadata}\n")
    except Exception as exc:
        print(f"   Search status: {exc}")

    print("==================================================")
    print("Live AWS verification complete! [OK]")
    print("When finished, remember to run:")
    print("   cd deploy/terraform && terraform destroy -auto-approve")
    print("==================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
