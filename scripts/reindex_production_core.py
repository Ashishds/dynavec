"""
Re-index all documents in the 'production-core' namespace in AWS DynamoDB & S3 Vectors
using the enhanced stemmed, stopword-filtered LocalDeterministicEmbedder.
"""

from __future__ import annotations

import math
import os
import re
import sys
import time
from pathlib import Path

# Ensure UTF-8 stdout
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "src"))

# Load .env
env_file = root_dir / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import boto3
from dynavec import Document, Dynavec, DynavecConfig
from dynavec.embeddings.base import Embedder

DIM = 16

ENGLISH_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "as", "is", "was", "are", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "how", "what", "which", "who", "whom",
    "this", "that", "these", "those", "can", "could", "will", "would", "shall", "should",
    "it", "its", "we", "our", "you", "your", "they", "their", "so", "if", "not",
}


def _stem_token(w: str) -> str:
    w = w.lower().strip()
    if w in ("transfomer", "transfomers", "transforming"):
        return "transform"
    if w.startswith("position"):
        return "position"
    if w.startswith("encod"):
        return "encod"
    if w.startswith("attent"):
        return "attent"
    if w.startswith("decod"):
        return "decod"
    w = re.sub(r"(al|ing|s|ed|er|ers|ion|ions|ment|ments|ive|ly)$", "", w)
    return w


class LocalDeterministicEmbedder(Embedder):
    def __init__(self, dimension: int = DIM) -> None:
        self.dimension = dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        import hashlib
        out = []
        for t in texts:
            v = [0.0] * self.dimension
            raw_words = re.findall(r"\b[a-zA-Z0-9_]+\b", t.lower())
            words = [_stem_token(w) for w in raw_words if w not in ENGLISH_STOPWORDS]
            for w in words:
                h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
                idx = h % self.dimension
                sign = 1.0 if ((h >> 8) & 1) else -1.0
                v[idx] += sign
            norm = math.sqrt(sum(x * x for x in v)) or 1e-9
            out.append([x / norm for x in v])
        return out


def main():
    region = os.environ.get("AWS_REGION", "us-east-1")
    table = os.environ.get("DYNAVEC_TABLE", "dynavec_docs")
    bucket = os.environ.get("DYNAVEC_VECTOR_BUCKET", "dynavec-vectors-212919533030")
    index = os.environ.get("DYNAVEC_INDEX", "docs-index")

    print(f"Scanning DynamoDB table '{table}' for 'production-core' items...")
    ddb = boto3.client("dynamodb", region_name=region)
    paginator = ddb.get_paginator("scan")
    page_iterator = paginator.paginate(
        TableName=table,
        FilterExpression="begins_with(pk, :prefix)",
        ExpressionAttributeValues={":prefix": {"S": "production-core#"}},
    )

    raw_items = []
    for page in page_iterator:
        raw_items.extend(page.get("Items", []))

    print(f"Found {len(raw_items)} documents in DynamoDB under 'production-core'.")
    if not raw_items:
        print("No documents found to reindex.")
        return

    docs: list[Document] = []
    for it in raw_items:
        pk = it.get("pk", {}).get("S", "")
        # doc_id is the part after the prefix
        doc_id = pk.split("#", 1)[1] if "#" in pk else pk
        # decode url-encoded hash signs if needed
        doc_id = doc_id.replace("%23", "#")
        text = it.get("text", {}).get("S", "")
        # convert metadata if present
        meta = {}
        raw_meta = it.get("metadata", {}).get("M", {})
        for k, v in raw_meta.items():
            if "S" in v:
                meta[k] = v["S"]
            elif "N" in v:
                meta[k] = int(v["N"]) if "." not in v["N"] else float(v["N"])
            elif "BOOL" in v:
                meta[k] = v["BOOL"]

        docs.append(Document(id=doc_id, text=text, metadata=meta))

    print(f"Embedding and upserting {len(docs)} documents into Amazon S3 Vectors...")
    cfg = DynavecConfig(
        vector_bucket=bucket,
        index=index,
        table=table,
        dimension=DIM,
        distance_metric="cosine",
        region=region,
        auto_provision=False,
    )
    db = Dynavec(
        cfg,
        embedder=LocalDeterministicEmbedder(DIM),
    )

    t0 = time.perf_counter()
    res = db.upsert(docs, namespace="production-core")
    elapsed = time.perf_counter() - t0

    print(f"[SUCCESS] Re-indexed {res.count} documents in {elapsed:.2f}s into 'production-core'.")


if __name__ == "__main__":
    main()
