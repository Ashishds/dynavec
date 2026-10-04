"""Tests for dynavec.agents.testing framework."""


from dynavec.agents import (
    AgentGraph,
    ContainsAssertion,
    ExactMatchAssertion,
    ExpressionAssertion,
    MaxLatencyAssertion,
    NodeVisitedAssertion,
    RagasMetricAssertion,
    TestCase,
    TestRunner,
    TestSuite,
)
from dynavec.agents.nodes import FunctionNode, GuardNode


def _mock_retriever(state):
    state["retrieved"] = [
        "Dynavec provides serverless sub-10ms vector search on AWS S3.",
        "It decouples cold storage in S3 from hot metadata indexing in DynamoDB.",
    ]
    state["confidence"] = 0.92
    return state


def _mock_synthesizer(state):
    state["answer"] = (
        "Dynavec achieves sub-10ms vector search by decoupling S3 vectors from DynamoDB metadata."
    )
    state["tokens"] = 42
    return state


def _make_sample_graph():
    return (
        AgentGraph("test-rag-graph")
        .add_node("retrieve", FunctionNode(_mock_retriever))
        .add_node("guard", GuardNode(threshold=0.5, score_field="confidence"))
        .add_node("synthesize", FunctionNode(_mock_synthesizer))
        .add_edge("retrieve", "guard")
        .add_edge("guard", "synthesize")
        .set_entry("retrieve")
    )


class TestAssertions:
    def test_exact_match(self):
        graph = _make_sample_graph()
        result = graph.run({"query": "test"})
        case = TestCase("c1", {"query": "test"})

        a_pass = ExactMatchAssertion("tokens", 42)
        r_pass = a_pass.evaluate(result, case)
        assert r_pass.passed is True

        a_fail = ExactMatchAssertion("tokens", 999)
        r_fail = a_fail.evaluate(result, case)
        assert r_fail.passed is False

    def test_contains(self):
        graph = _make_sample_graph()
        result = graph.run({"query": "test"})
        case = TestCase("c1", {"query": "test"})

        a1 = ContainsAssertion("answer", "sub-10ms")
        assert a1.evaluate(result, case).passed is True

        a2 = ContainsAssertion("answer", "NONEXISTENT_KEYWORD")
        assert a2.evaluate(result, case).passed is False

        # Missing key
        a3 = ContainsAssertion("missing_key", "foo")
        assert a3.evaluate(result, case).passed is False

    def test_expression(self):
        graph = _make_sample_graph()
        result = graph.run({"query": "test"})
        case = TestCase("c1", {"query": "test"})

        e1 = ExpressionAssertion("tokens >= 40 and tokens < 50")
        assert e1.evaluate(result, case).passed is True

        e2 = ExpressionAssertion("tokens == 100")
        assert e2.evaluate(result, case).passed is False

    def test_node_visited(self):
        graph = _make_sample_graph()
        result = graph.run({"query": "test"})
        case = TestCase("c1", {"query": "test"})

        v1 = NodeVisitedAssertion("synthesize", must_visit=True)
        assert v1.evaluate(result, case).passed is True

        v2 = NodeVisitedAssertion("nonexistent_node", must_visit=True)
        assert v2.evaluate(result, case).passed is False

        v3 = NodeVisitedAssertion("nonexistent_node", must_visit=False)
        assert v3.evaluate(result, case).passed is True

    def test_max_latency(self):
        graph = _make_sample_graph()
        result = graph.run({"query": "test"})
        case = TestCase("c1", {"query": "test"})

        l1 = MaxLatencyAssertion(max_ms=10000.0)
        assert l1.evaluate(result, case).passed is True

        l2 = MaxLatencyAssertion(max_ms=0.0001)
        assert l2.evaluate(result, case).passed is False

    def test_ragas_faithfulness(self):
        graph = _make_sample_graph()
        result = graph.run({"query": "how does search work?"})
        case = TestCase(
            "ragas-case",
            input_state={"query": "how does search work?"},
            context_docs=[
                "Dynavec achieves sub-10ms vector search by decoupling S3 vectors from DynamoDB metadata."
            ],
        )

        rf = RagasMetricAssertion("faithfulness", min_score=0.7)
        res = rf.evaluate(result, case)
        assert res.passed is True
        assert res.score is not None
        assert res.score >= 0.7

    def test_ragas_answer_relevance(self):
        graph = _make_sample_graph()
        result = graph.run({"query": "vector search S3"})
        case = TestCase(
            "rel-case",
            input_state={"query": "vector search S3"},
        )

        ra = RagasMetricAssertion("answer_relevance", min_score=0.5)
        res = ra.evaluate(result, case)
        assert res.passed is True
        assert res.score is not None

    def test_ragas_custom_eval_fn(self):
        graph = _make_sample_graph()
        result = graph.run({"query": "test"})
        case = TestCase("custom", {"query": "test"}, context_docs=["doc1"])

        def my_eval(q, ctx, ans):
            return 0.95

        rc = RagasMetricAssertion("custom_score", min_score=0.9, eval_fn=my_eval)
        res = rc.evaluate(result, case)
        assert res.passed is True
        assert res.score == 0.95


class TestSuiteAndRunner:
    def test_full_test_suite_run(self):
        graph = _make_sample_graph()
        suite = TestSuite("qa-suite", "Regression QA suite for RAG")

        c1 = (
            TestCase(
                "query-explanation",
                input_state={"query": "explain sub-10ms search"},
                context_docs=[
                    "Dynavec achieves sub-10ms vector search by decoupling S3 vectors from DynamoDB metadata."
                ],
            )
            .add_assertion(ContainsAssertion("answer", "sub-10ms"))
            .add_assertion(NodeVisitedAssertion("synthesize"))
            .add_assertion(RagasMetricAssertion("faithfulness", min_score=0.6))
            .add_assertion(MaxLatencyAssertion(max_ms=5000.0))
        )

        c2 = (
            TestCase(
                "token-limit",
                input_state={"query": "test token limit"},
            )
            .add_assertion(ExactMatchAssertion("tokens", 42))
            .add_assertion(ExpressionAssertion("tokens < 100"))
        )

        suite.add_case(c1).add_case(c2)

        runner = TestRunner()
        suite_res = runner.run(graph, suite)

        assert suite_res.total_cases == 2
        assert suite_res.passed_cases == 2
        assert suite_res.failed_cases == 0
        assert suite_res.pass_rate == 1.0
        assert suite_res.passed is True
        assert "faithfulness" in suite_res.avg_ragas_metrics

        # Test dictionary export
        d = suite_res.to_dict()
        assert d["passed"] is True
        assert len(d["cases"]) == 2

        # Test JUnit XML export
        xml = suite_res.to_junit_xml()
        assert "<testsuite" in xml
        assert '<testcase name="query-explanation"' in xml
        assert "</testsuite>" in xml

    def test_failed_assertions_tracked(self):
        graph = _make_sample_graph()
        suite = TestSuite("failing-suite")

        c_fail = TestCase(
            "bad-expectation",
            input_state={"query": "test"},
        ).add_assertion(ExactMatchAssertion("tokens", 9999))

        suite.add_case(c_fail)

        runner = TestRunner()
        res = runner.run(graph, suite)

        assert res.passed is False
        assert res.failed_cases == 1
        assert res.pass_rate == 0.0

        xml = res.to_junit_xml()
        assert "<failure" in xml
