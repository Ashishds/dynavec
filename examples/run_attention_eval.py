"""Run retrieval quality evaluation against the live AWS Dynavec index.

Loads the ground-truth attention paper Q&A dataset, runs each query against
the live AWS index, computes Recall@k, MRR, and nDCG@k, then saves timestamped
JSON to evals/ so the EvalTrends dashboard chart populates.

Usage:
    python examples/run_attention_eval.py [--namespace production-core]
"""

from __future__ import annotations

import os
import sys
import time
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

import argparse

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("ERROR: sentence-transformers not installed.")
    sys.exit(1)

from dynavec import Dynavec, DynavecConfig
from dynavec.embeddings.base import Embedder
from dynavec.eval import EvalDataset, run_eval

DIM = 384
MODEL_NAME = "all-MiniLM-L6-v2"


class STEmbedder(Embedder):
    def __init__(self):
        self._st = SentenceTransformer(MODEL_NAME)
        if hasattr(self._st, "get_embedding_dimension"):
            self.dimension = self._st.get_embedding_dimension()
        else:
            self.dimension = self._st.get_sentence_embedding_dimension()

    def embed_documents(self, texts):
        return self._st.encode(texts, normalize_embeddings=True, convert_to_numpy=True).tolist()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", default="production-core")
    parser.add_argument("--ks", default="1,3,5,10", help="Comma-separated k values")
    args = parser.parse_args()
    ks = [int(k) for k in args.ks.split(",")]

    region = os.environ.get("AWS_REGION", "us-east-1")
    bucket = os.environ.get("DYNAVEC_VECTOR_BUCKET", "dynavec-vectors-212919533030")
    table  = os.environ.get("DYNAVEC_TABLE", "dynavec_docs")
    index  = os.environ.get("DYNAVEC_INDEX", "docs-index")

    qa_path = Path(__file__).resolve().parent.parent / "evals" / "attention_paper_qa.json"
    if not qa_path.exists():
        print(f"ERROR: eval dataset not found: {qa_path}")
        sys.exit(1)

    # Load dataset manually to strip extra fields (expected_page, notes)
    # that are in our QA JSON but not accepted by EvalQuery
    import json as _json
    raw_data = _json.loads(qa_path.read_text(encoding="utf-8-sig"))
    from dynavec.eval import EvalQuery
    queries = [
        EvalQuery(text=q["text"], relevant_ids=q["relevant_ids"])
        for q in raw_data.get("queries", [])
    ]
    from dynavec.eval import EvalDataset as _EvalDataset
    dataset = _EvalDataset(
        queries=queries,
        name=raw_data.get("name", "attention-paper-qa"),
        description=raw_data.get("description", ""),
    )

    print("=" * 60)
    print(" Dynavec Retrieval Quality Evaluation")
    print(f" Dataset:   {dataset.name} ({len(dataset)} queries)")
    print(f" Namespace: {args.namespace}")
    print(f" Ks:        {ks}")
    print("=" * 60)

    print("\n Loading embedder ...")
    embedder = STEmbedder()
    print(f"  {MODEL_NAME} ({DIM}-dim) loaded.")

    cfg = DynavecConfig(
        vector_bucket=bucket, index=index, table=table,
        dimension=DIM, distance_metric="cosine", region=region, auto_provision=False
    )
    db = Dynavec(cfg, embedder=embedder)
    print("\n Running eval ...")
    t0 = time.perf_counter()
    result = run_eval(db, dataset, ks=ks, namespace=args.namespace)
    elapsed = time.perf_counter() - t0

    print("\n RESULTS:")
    print(f"  MRR:      {result.mrr:.4f}")
    for k in ks:
        print(f"  Recall@{k}: {result.recall[k]:.4f}  |  nDCG@{k}: {result.ndcg[k]:.4f}")
    print(f"\n  Total time: {elapsed:.1f}s ({len(dataset)} queries)")

    # Save timestamped eval JSON using the built-in to_json method
    evals_dir = Path(__file__).resolve().parent.parent / "evals"
    evals_dir.mkdir(exist_ok=True)
    ts = int(time.time())
    out_path = evals_dir / f"eval-{ts}.json"
    result.to_json(out_path)

    # Patch in extra metadata
    import json
    data = json.loads(out_path.read_text(encoding="utf-8"))
    data["timestamp"] = ts
    data["embedder"] = MODEL_NAME
    data["namespace"] = args.namespace
    data["elapsed_sec"] = round(elapsed, 2)
    # dashboard expects recall/ndcg with integer keys but recall@k in summary
    data["mrr"] = round(result.mrr, 4)
    for k in ks:
        data[f"recall@{k}"] = round(result.recall[k], 4)
        data[f"ndcg@{k}"] = round(result.ndcg[k], 4)
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"\n Saved eval results to: {out_path.name}")
    print(" EvalTrends chart on dashboard will now show this benchmark!")


if __name__ == "__main__":
    main()
