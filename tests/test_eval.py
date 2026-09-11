"""Tests for the offline retrieval quality evaluation module."""

import json

import pytest

from dynavec.eval import (
    EvalDataset,
    EvalQuery,
    EvalResult,
    QueryResult,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
)

# -------------------------------------------------------------------- recall@k


class TestRecallAtK:
    def test_perfect_recall(self):
        retrieved = ["a", "b", "c", "d"]
        relevant = {"a", "b"}
        assert recall_at_k(retrieved, relevant, k=4) == 1.0

    def test_partial_recall(self):
        retrieved = ["a", "x", "y", "b"]
        relevant = {"a", "b", "c"}
        assert recall_at_k(retrieved, relevant, k=4) == pytest.approx(2 / 3)

    def test_zero_recall(self):
        retrieved = ["x", "y", "z"]
        relevant = {"a", "b"}
        assert recall_at_k(retrieved, relevant, k=3) == 0.0

    def test_k_limits_search(self):
        retrieved = ["x", "a", "b"]
        relevant = {"a", "b"}
        assert recall_at_k(retrieved, relevant, k=1) == 0.0
        assert recall_at_k(retrieved, relevant, k=2) == 0.5
        assert recall_at_k(retrieved, relevant, k=3) == 1.0

    def test_empty_relevant_returns_zero(self):
        assert recall_at_k(["a", "b"], set(), k=2) == 0.0

    def test_empty_retrieved_returns_zero(self):
        assert recall_at_k([], {"a"}, k=5) == 0.0

    def test_k_greater_than_retrieved(self):
        retrieved = ["a"]
        relevant = {"a", "b"}
        assert recall_at_k(retrieved, relevant, k=100) == 0.5


# -------------------------------------------------------------------- MRR


class TestReciprocalRank:
    def test_first_position(self):
        assert reciprocal_rank(["a", "b", "c"], {"a"}) == 1.0

    def test_second_position(self):
        assert reciprocal_rank(["x", "a", "c"], {"a"}) == 0.5

    def test_third_position(self):
        assert reciprocal_rank(["x", "y", "a"], {"a"}) == pytest.approx(1 / 3)

    def test_not_found(self):
        assert reciprocal_rank(["x", "y", "z"], {"a"}) == 0.0

    def test_multiple_relevant_uses_first(self):
        # RR = 1 / rank of FIRST relevant doc
        assert reciprocal_rank(["x", "a", "b"], {"a", "b"}) == 0.5

    def test_empty_relevant(self):
        assert reciprocal_rank(["a", "b"], set()) == 0.0


# -------------------------------------------------------------------- nDCG@k


class TestNDCGAtK:
    def test_perfect_ranking(self):
        # All relevant docs at the top
        retrieved = ["a", "b", "x", "y"]
        relevant = {"a", "b"}
        result = ndcg_at_k(retrieved, relevant, k=4)
        assert result == pytest.approx(1.0)

    def test_inverse_ranking(self):
        # Relevant docs at the bottom
        retrieved = ["x", "y", "a", "b"]
        relevant = {"a", "b"}
        result = ndcg_at_k(retrieved, relevant, k=4)
        # DCG = 1/log2(4) + 1/log2(5) = 0.5 + 0.431 = 0.931
        # IDCG = 1/log2(2) + 1/log2(3) = 1.0 + 0.631 = 1.631
        assert result < 1.0
        assert result > 0.0

    def test_no_relevant_docs_found(self):
        assert ndcg_at_k(["x", "y"], {"a"}, k=2) == 0.0

    def test_empty_relevant(self):
        assert ndcg_at_k(["a", "b"], set(), k=2) == 0.0

    def test_single_relevant_at_k1(self):
        retrieved = ["a", "x", "y"]
        relevant = {"a"}
        assert ndcg_at_k(retrieved, relevant, k=1) == 1.0

    def test_single_relevant_at_k1_not_found(self):
        retrieved = ["x", "a", "y"]
        relevant = {"a"}
        assert ndcg_at_k(retrieved, relevant, k=1) == 0.0


# ---------------------------------------------------------------- EvalDataset


class TestEvalDataset:
    def test_len(self):
        ds = EvalDataset(
            queries=[
                EvalQuery(text="q1", relevant_ids=["a"]),
                EvalQuery(text="q2", relevant_ids=["b"]),
            ]
        )
        assert len(ds) == 2

    def test_from_json(self, tmp_path):
        data = {
            "name": "test-dataset",
            "description": "for testing",
            "queries": [
                {"text": "hello", "relevant_ids": ["doc1", "doc2"]},
                {"text": "world", "relevant_ids": ["doc3"]},
            ],
        }
        path = tmp_path / "eval.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        ds = EvalDataset.from_json(path)
        assert ds.name == "test-dataset"
        assert len(ds) == 2
        assert ds.queries[0].text == "hello"
        assert ds.queries[0].relevant_ids == ["doc1", "doc2"]

    def test_from_json_minimal(self, tmp_path):
        data = {"queries": [{"text": "q", "relevant_ids": []}]}
        path = tmp_path / "minimal.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        ds = EvalDataset.from_json(path)
        assert ds.name == "unnamed"
        assert len(ds) == 1


# ---------------------------------------------------------------- EvalResult


class TestEvalResult:
    def test_summary_format(self):
        result = EvalResult(
            dataset_name="test",
            ks=[1, 5],
            n_queries=10,
            per_query=[],
            recall={1: 0.3, 5: 0.8},
            mrr=0.55,
            ndcg={1: 0.4, 5: 0.7},
        )
        s = result.summary()
        assert s["dataset"] == "test"
        assert s["n_queries"] == 10
        assert s["mrr"] == 0.55
        assert "recall@1" in s
        assert "recall@5" in s
        assert "ndcg@1" in s
        assert "ndcg@5" in s

    def test_to_json(self, tmp_path):
        result = EvalResult(
            dataset_name="test",
            ks=[1, 5],
            n_queries=2,
            per_query=[
                QueryResult(
                    query_text="q1",
                    retrieved_ids=["a", "b"],
                    relevant_ids=["a"],
                    recall={1: 1.0, 5: 1.0},
                    reciprocal_rank=1.0,
                    ndcg={1: 1.0, 5: 1.0},
                ),
            ],
            recall={1: 1.0, 5: 1.0},
            mrr=1.0,
            ndcg={1: 1.0, 5: 1.0},
        )
        path = tmp_path / "results.json"
        result.to_json(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["dataset"] == "test"
        assert data["mrr"] == 1.0
        assert len(data["per_query"]) == 1


# --------------------------------------------------------- metric properties


class TestMetricProperties:
    """Mathematical properties that must always hold."""

    def test_recall_monotonically_increases_with_k(self):
        retrieved = ["x", "a", "y", "b", "z"]
        relevant = {"a", "b"}
        values = [recall_at_k(retrieved, relevant, k) for k in range(1, 6)]
        for i in range(1, len(values)):
            assert values[i] >= values[i - 1]

    def test_recall_bounded_0_1(self):
        retrieved = ["a", "b", "c"]
        relevant = {"a", "d"}
        for k in [1, 2, 3, 10]:
            v = recall_at_k(retrieved, relevant, k)
            assert 0.0 <= v <= 1.0

    def test_mrr_bounded_0_1(self):
        for retrieved in [["a", "b"], ["x", "y"], ["x", "a"]]:
            v = reciprocal_rank(retrieved, {"a"})
            assert 0.0 <= v <= 1.0

    def test_ndcg_bounded_0_1(self):
        retrieved = ["x", "a", "y", "b"]
        relevant = {"a", "b"}
        for k in [1, 2, 3, 4]:
            v = ndcg_at_k(retrieved, relevant, k)
            assert 0.0 <= v <= 1.0

    def test_ndcg_perfect_is_one(self):
        retrieved = ["a", "b", "c"]
        relevant = {"a", "b"}
        assert ndcg_at_k(retrieved, relevant, k=3) == pytest.approx(1.0)
