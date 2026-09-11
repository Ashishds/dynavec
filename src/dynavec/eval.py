"""Offline retrieval-quality evaluation: Recall@k, MRR, nDCG.

Run this against a ground-truth dataset (query → relevant doc IDs) to
measure how well your index, embedder, and retrieval pipeline perform.
Results are pure Python dicts — easy to print, log, or chart on the dashboard.

Example::

    from dynavec.eval import EvalDataset, EvalQuery, run_eval

    dataset = EvalDataset(queries=[
        EvalQuery(text="how do cells make energy?", relevant_ids=["bio-1", "bio-2"]),
        EvalQuery(text="rocket propulsion", relevant_ids=["space-1"]),
    ])
    result = run_eval(db, dataset, ks=[1, 5, 10])
    print(result.summary())   # {"recall@1": 0.50, "recall@5": 0.80, ...}
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .client import Dynavec


@dataclass
class EvalQuery:
    """One evaluation query with its ground-truth relevant document IDs."""

    text: str
    relevant_ids: list[str]
    vector: list[float] | None = None  # optional pre-computed query vector
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalDataset:
    """A collection of evaluation queries."""

    queries: list[EvalQuery]
    name: str = "unnamed"
    description: str = ""

    def __len__(self) -> int:
        return len(self.queries)

    @classmethod
    def from_json(cls, path: str | Path) -> EvalDataset:
        """Load from a JSON file.

        Expected format::

            {
                "name": "my-eval",
                "queries": [
                    {"text": "...", "relevant_ids": ["id1", "id2"]},
                    ...
                ]
            }
        """
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        queries = [EvalQuery(**q) for q in data.get("queries", [])]
        return cls(
            queries=queries,
            name=data.get("name", "unnamed"),
            description=data.get("description", ""),
        )


@dataclass
class QueryResult:
    """Per-query evaluation scores."""

    query_text: str
    retrieved_ids: list[str]
    relevant_ids: list[str]
    recall: dict[int, float]  # k → recall@k
    reciprocal_rank: float
    ndcg: dict[int, float]  # k → nDCG@k


@dataclass
class EvalResult:
    """Aggregate evaluation result across all queries."""

    dataset_name: str
    ks: list[int]
    n_queries: int
    per_query: list[QueryResult]

    # Aggregate metrics
    recall: dict[int, float]  # k → mean recall@k
    mrr: float  # Mean Reciprocal Rank
    ndcg: dict[int, float]  # k → mean nDCG@k

    def summary(self) -> dict[str, Any]:
        """Flat dict for easy logging/display."""
        out: dict[str, Any] = {
            "dataset": self.dataset_name,
            "n_queries": self.n_queries,
            "mrr": round(self.mrr, 4),
        }
        for k in self.ks:
            out[f"recall@{k}"] = round(self.recall[k], 4)
            out[f"ndcg@{k}"] = round(self.ndcg[k], 4)
        return out

    def to_json(self, path: str | Path) -> None:
        """Save results to a JSON file."""
        data = {
            "dataset": self.dataset_name,
            "ks": self.ks,
            "n_queries": self.n_queries,
            "mrr": self.mrr,
            "recall": {str(k): v for k, v in self.recall.items()},
            "ndcg": {str(k): v for k, v in self.ndcg.items()},
            "per_query": [asdict(q) for q in self.per_query],
        }
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


# -------------------------------------------------------------------- metrics


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """Fraction of relevant documents found in the top-k retrieved."""
    if not relevant:
        return 0.0
    found = sum(1 for doc_id in retrieved[:k] if doc_id in relevant)
    return found / len(relevant)


def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    """1 / (rank of the first relevant document). 0 if none found."""
    for i, doc_id in enumerate(retrieved, 1):
        if doc_id in relevant:
            return 1.0 / i
    return 0.0


def _dcg(gains: list[float], k: int) -> float:
    """Discounted cumulative gain at k."""
    total = 0.0
    for i, g in enumerate(gains[:k]):
        total += g / math.log2(i + 2)  # i+2 because rank is 1-indexed
    return total


def ndcg_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """Normalized Discounted Cumulative Gain at k.

    Binary relevance: gain = 1 if relevant, 0 otherwise.
    """
    if not relevant:
        return 0.0
    gains = [1.0 if doc_id in relevant else 0.0 for doc_id in retrieved[:k]]
    dcg = _dcg(gains, k)
    # Ideal: all relevant docs ranked first
    ideal_gains = [1.0] * min(len(relevant), k)
    idcg = _dcg(ideal_gains, k)
    if idcg == 0.0:
        return 0.0
    return dcg / idcg


# ---------------------------------------------------------------- runner


def run_eval(
    db: Dynavec,
    dataset: EvalDataset,
    *,
    ks: list[int] | None = None,
    namespace: str = "default",
    **search_kwargs: Any,
) -> EvalResult:
    """Run all queries in ``dataset`` against ``db`` and compute metrics.

    Parameters
    ----------
    db:
        A configured :class:`Dynavec` client.
    dataset:
        The evaluation dataset.
    ks:
        List of k values to compute Recall@k and nDCG@k for.
        Defaults to ``[1, 5, 10, 20]``.
    namespace:
        Namespace to search in.
    **search_kwargs:
        Extra keyword arguments forwarded to ``db.search()``
        (e.g. ``filter``, ``rescore``, ``rerank``).
    """
    if ks is None:
        ks = [1, 5, 10, 20]
    ks = sorted(ks)
    max_k = max(ks)

    per_query: list[QueryResult] = []
    all_recall: dict[int, list[float]] = {k: [] for k in ks}
    all_ndcg: dict[int, list[float]] = {k: [] for k in ks}
    all_rr: list[float] = []

    for eq in dataset.queries:
        results = db.search(
            query=eq.text if eq.vector is None else None,
            vector=eq.vector,
            top_k=max_k,
            namespace=namespace,
            **search_kwargs,
        )
        retrieved_ids = [r.id for r in results]
        relevant_set = set(eq.relevant_ids)

        q_recall: dict[int, float] = {}
        q_ndcg: dict[int, float] = {}
        for k in ks:
            q_recall[k] = recall_at_k(retrieved_ids, relevant_set, k)
            q_ndcg[k] = ndcg_at_k(retrieved_ids, relevant_set, k)
            all_recall[k].append(q_recall[k])
            all_ndcg[k].append(q_ndcg[k])

        rr = reciprocal_rank(retrieved_ids, relevant_set)
        all_rr.append(rr)

        per_query.append(
            QueryResult(
                query_text=eq.text,
                retrieved_ids=retrieved_ids,
                relevant_ids=eq.relevant_ids,
                recall=q_recall,
                reciprocal_rank=rr,
                ndcg=q_ndcg,
            )
        )

    n = len(dataset.queries) or 1
    return EvalResult(
        dataset_name=dataset.name,
        ks=ks,
        n_queries=len(dataset.queries),
        per_query=per_query,
        recall={k: sum(vs) / n for k, vs in all_recall.items()},
        mrr=sum(all_rr) / n,
        ndcg={k: sum(vs) / n for k, vs in all_ndcg.items()},
    )
