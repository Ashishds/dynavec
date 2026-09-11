"""Dynavec Portfolio Showcase & Semantic Article Ingestion.

Ingests rich real-world articles into your live AWS DynamoDB table (dynavec_docs)
and Amazon S3 Vectors, then runs semantic queries with real-time telemetry.

Usage:
    python examples/portfolio_demo.py
"""

from __future__ import annotations

import math
import os
import sys
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

from dynavec import Document, Dynavec, DynavecConfig
from dynavec.embeddings.base import Embedder

DIM = 16


class LocalDeterministicEmbedder(Embedder):
    """Zero-dependency deterministic vector embedder."""

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


ARTICLES = [
    # --- Domain: Cloud & Serverless ---
    Document(
        id="cloud-01",
        text="Amazon DynamoDB achieves single-digit millisecond latency at any scale by automatically partitioning SSD-backed storage partitions.",
        metadata={"domain": "cloud", "topic": "dynamodb", "level": "expert", "year": 2026},
    ),
    Document(
        id="cloud-02",
        text="Serverless vector databases eliminate expensive idle EC2 compute clusters by charging strictly on a pay-per-query execution model.",
        metadata={"domain": "cloud", "topic": "cost", "level": "beginner", "year": 2026},
    ),
    Document(
        id="cloud-03",
        text="Amazon S3 Vectors provides cloud-native serverless Approximate Nearest Neighbor (ANN) indexing for billion-scale embeddings.",
        metadata={"domain": "cloud", "topic": "s3vectors", "level": "intermediate", "year": 2026},
    ),
    Document(
        id="cloud-04",
        text="VPC Gateway Endpoints route DynamoDB and S3 traffic over the internal AWS private backbone, completely eliminating NAT Gateway data egress costs.",
        metadata={"domain": "cloud", "topic": "networking", "level": "advanced", "year": 2026},
    ),
    # --- Domain: AI & Retrieval-Augmented Generation (RAG) ---
    Document(
        id="ai-01",
        text="Retrieval-Augmented Generation (RAG) grounds Large Language Models on verified company knowledge bases to prevent hallucinations.",
        metadata={"domain": "ai", "topic": "rag", "level": "beginner", "year": 2026},
    ),
    Document(
        id="ai-02",
        text="Dense vector embeddings represent semantic meaning as high-dimensional coordinates, allowing cosine similarity matching across diverse vocabularies.",
        metadata={"domain": "ai", "topic": "embeddings", "level": "intermediate", "year": 2026},
    ),
    Document(
        id="ai-03",
        text="Maximal Marginal Relevance (MMR) balances query relevance with result diversity, preventing redundant search snippets in LLM context windows.",
        metadata={"domain": "ai", "topic": "reranking", "level": "advanced", "year": 2026},
    ),
    Document(
        id="ai-04",
        text="Semantic caching intercepts repetitive or near-duplicate queries locally, serving sub-millisecond similarity results while saving 70%+ in LLM API spend.",
        metadata={"domain": "ai", "topic": "caching", "level": "intermediate", "year": 2026},
    ),
    # --- Domain: DevOps & Infrastructure as Code ---
    Document(
        id="devops-01",
        text="Terraform enables deterministic Infrastructure as Code (IaC), allowing teams to provision and tear down cloud environments with one command.",
        metadata={"domain": "devops", "topic": "terraform", "level": "intermediate", "year": 2026},
    ),
    Document(
        id="devops-02",
        text="IAM least-privilege policies restrict database access strictly to required table ARNs, minimizing blast radius and securing cloud credentials.",
        metadata={"domain": "devops", "topic": "security", "level": "expert", "year": 2026},
    ),
    Document(
        id="devops-03",
        text="Automated CI/CD security scanning with pip-audit identifies supply-chain vulnerabilities in Python dependencies before production builds.",
        metadata={"domain": "devops", "topic": "security", "level": "intermediate", "year": 2026},
    ),
    Document(
        id="devops-04",
        text="Int8 scalar quantization compresses float32 embeddings into 8-bit integers, providing a 4x reduction in vector memory with over 98% accuracy retention.",
        metadata={"domain": "ai", "topic": "quantization", "level": "advanced", "year": 2026},
    ),
]


def main() -> int:
    region = os.environ.get("AWS_REGION", "us-east-1")
    bucket = os.environ.get("DYNAVEC_VECTOR_BUCKET", "dynavec-vectors-212919533030")
    table = os.environ.get("DYNAVEC_TABLE", "dynavec_docs")
    index = os.environ.get("DYNAVEC_INDEX", "docs-index")

    print("\n" + "=" * 65)
    print("      DYNAVEC ENTERPRISE PORTFOLIO SHOWCASE: LIVE AWS CLOUD      ")
    print("=" * 65)
    print(f"Target AWS Region:      {region}")
    print(f"DynamoDB Document Table: {table}")
    print(f"S3 Vector Bucket:        {bucket}")
    print(f"Index Dimensions:        {DIM} float32")
    print("=" * 65 + "\n")

    cfg = DynavecConfig(
        vector_bucket=bucket,
        index=index,
        table=table,
        dimension=DIM,
        distance_metric="cosine",
        region=region,
        auto_provision=False,
    )

    print("Connecting to live AWS DynamoDB and S3 Vectors...")
    db = Dynavec(cfg, embedder=LocalDeterministicEmbedder(DIM))
    print("[OK] Connected to Dynavec AWS Client.\n")

    # 1. Ingest Articles
    namespace = "portfolio-demo"
    print(f"[STEP 1] Ingesting {len(ARTICLES)} curated enterprise articles into namespace '{namespace}'...")
    start_time = time.perf_counter()
    db.upsert(ARTICLES, namespace=namespace)
    duration_ms = (time.perf_counter() - start_time) * 1000
    print(f"         Successfully dual-written into DynamoDB & S3 in {duration_ms:.1f} ms!")
    print(f"         Total documents indexed: {len(ARTICLES)}\n")

    # 2. Realistic Search Queries
    test_queries = [
        {
            "title": "Query 1: Pure Semantic Search (Cloud Architecture)",
            "query": "How does DynamoDB achieve sub-millisecond database latency?",
            "filter": None,
            "rerank": None,
        },
        {
            "title": "Query 2: Filtered Semantic Search (AI & Quantization)",
            "query": "vector memory compression and accuracy",
            "filter": {"domain": "ai"},
            "rerank": None,
        },
        {
            "title": "Query 3: MMR Reranked Search (Diversity in RAG)",
            "query": "serverless cloud cost savings and infrastructure",
            "filter": None,
            "rerank": "mmr",
        },
    ]

    for q in test_queries:
        print("-" * 65)
        print(f"[SEARCH] {q['title']}")
        print(f"         Query: \"{q['query']}\"")
        if q["filter"]:
            print(f"         Filter: {q['filter']}")
        if q["rerank"]:
            print(f"         Rerank: {q['rerank'].upper()}")

        t0 = time.perf_counter()
        results = db.search(
            q["query"],
            top_k=2,
            namespace=namespace,
            filter=q["filter"],
            rerank=q["rerank"],
        )
        t_search = (time.perf_counter() - t0) * 1000

        print(f"         Executed in {t_search:.2f} ms | Found {len(results)} matches:\n")
        for i, hit in enumerate(results, start=1):
            print(f"         #{i} [Score: {hit.score:.4f}] ID: {hit.id}")
            print(f"             \"{hit.text}\"")
            print(f"             Metadata: {hit.metadata}\n")

    print("=" * 65)
    print("Portfolio Demo Ingestion Complete! [OK]")
    print(f"View live traces in your Dashboard: http://localhost:3000")
    print(f"View DynamoDB items in AWS Console: https://us-east-1.console.aws.amazon.com/dynamodbv2")
    print("=" * 65 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
