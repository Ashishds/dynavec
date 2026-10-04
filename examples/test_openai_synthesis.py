"""Verify the OpenAI synthesis path is working end-to-end.

This script queries the live AWS index and forces the OpenAI synthesizer
to generate a grounded answer, printing the result with citation and latency.

Usage:
    python examples/test_openai_synthesis.py
"""
from __future__ import annotations
import os, sys, time
from pathlib import Path

env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if v.strip():
                os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dynavec import Dynavec, DynavecConfig
from dynavec.embeddings.sentence_transformers import SentenceTransformerEmbedder
from dynavec.rag_synthesizer import OpenAISynthesizer

NAMESPACE = "production-core"
TEST_QUERIES = [
    "What is multi-head attention and how does it work?",
    "How does positional encoding work in transformers?",
    "What BLEU score did the transformer achieve?",
]

def search_result_to_dict(r):
    """Convert SearchResult object to dict for synthesizer."""
    return {
        "id": r.id,
        "text": r.text,
        "score": r.score,
        "metadata": dict(r.metadata or {}),
    }

def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set in .env")
        sys.exit(1)
    print(f"OPENAI_API_KEY: set (sk-...{api_key[-8:]})")

    print("\nLoading embedder (all-MiniLM-L6-v2 384-dim)...")
    embedder = SentenceTransformerEmbedder()
    cfg = DynavecConfig(
        vector_bucket=os.environ.get("DYNAVEC_VECTOR_BUCKET", "dynavec-vectors-212919533030"),
        index=os.environ.get("DYNAVEC_INDEX", "docs-index"),
        table=os.environ.get("DYNAVEC_TABLE", "dynavec_docs"),
        dimension=384, distance_metric="cosine",
        region=os.environ.get("AWS_REGION", "us-east-1"), auto_provision=False,
    )
    db = Dynavec(cfg, embedder=embedder)

    try:
        synth = OpenAISynthesizer()
        print(f"OpenAI synthesizer initialized: model={synth._model}")
    except Exception as exc:
        print(f"ERROR: Could not initialize OpenAI synthesizer: {exc}")
        sys.exit(1)

    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n{'='*60}")
        print(f"Query {i}: {query}")
        print("="*60)

        t0 = time.perf_counter()
        results = db.search(query, namespace=NAMESPACE, top_k=3)
        ann_ms = (time.perf_counter() - t0) * 1000

        if not results:
            print("  No results from AWS index. Was the paper ingested?")
            continue

        print(f"  AWS retrieval: {ann_ms:.0f}ms, {len(results)} results")
        for r in results[:2]:
            page = (r.metadata or {}).get("page", "?")
            print(f"  [Page {page}] score={r.score:.3f}: {r.text[:80]}...")

        # Convert SearchResult to dicts before passing to synthesizer
        chunks = [search_result_to_dict(r) for r in results]

        t1 = time.perf_counter()
        answer = synth.synthesize(query, chunks)
        llm_ms = (time.perf_counter() - t1) * 1000

        print(f"\n  SYNTHESIZED ({answer.model}, {llm_ms:.0f}ms, confidence={answer.confidence}):")
        print(f"  {answer.text[:350]}...")
        print(f"  Citations: {[c.id for c in answer.citations[:3]]}")
        conf_pct = int((answer.confidence_score or 0) * 100)
        print(f"  Confidence score: {conf_pct}%")

    print("\n\nOpenAI synthesis verification COMPLETE!")

if __name__ == "__main__":
    main()
