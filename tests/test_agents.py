"""Tests for the agent orchestration engine (pure, no AWS)."""

from __future__ import annotations

import pytest

from dynavec.agents import AgentGraph, AgentResult, AgentState, Edge
from dynavec.agents.base import NODE_REGISTRY, _eval_expr
from dynavec.agents.nodes import (
    FilterNode,
    FunctionNode,
    GuardNode,
    LLMNode,
    MapNode,
    PassthroughNode,
    ResponseNode,
    TransformNode,
)

# ======================================================================
# AgentState
# ======================================================================


class TestAgentState:
    def test_dict_behaviour(self):
        s = AgentState({"a": 1, "b": 2})
        assert s["a"] == 1
        assert len(s) == 2

    def test_set_returns_self(self):
        s = AgentState()
        ret = s.set("x", 42)
        assert ret is s
        assert s["x"] == 42


# ======================================================================
# Expression evaluator
# ======================================================================


class TestExprEval:
    def test_eq(self):
        assert _eval_expr("x == 5", {"x": 5}) is True
        assert _eval_expr("x == 5", {"x": 3}) is False

    def test_neq(self):
        assert _eval_expr("x != 5", {"x": 3}) is True
        assert _eval_expr("x != 5", {"x": 5}) is False

    def test_gt(self):
        assert _eval_expr("x > 3", {"x": 5}) is True
        assert _eval_expr("x > 3", {"x": 2}) is False

    def test_gte(self):
        assert _eval_expr("x >= 5", {"x": 5}) is True
        assert _eval_expr("x >= 5", {"x": 4}) is False

    def test_lt(self):
        assert _eval_expr("x < 5", {"x": 3}) is True
        assert _eval_expr("x < 5", {"x": 7}) is False

    def test_lte(self):
        assert _eval_expr("x <= 5", {"x": 5}) is True
        assert _eval_expr("x <= 5", {"x": 6}) is False

    def test_string_value(self):
        assert _eval_expr("intent == 'question'", {"intent": "question"}) is True
        assert _eval_expr('intent == "greeting"', {"intent": "greeting"}) is True

    def test_bool_value(self):
        assert _eval_expr("flag == True", {"flag": True}) is True
        assert _eval_expr("flag == False", {"flag": False}) is True

    def test_none_value(self):
        assert _eval_expr("x == None", {"x": None}) is True

    def test_float_value(self):
        assert _eval_expr("confidence >= 0.35", {"confidence": 0.5}) is True
        assert _eval_expr("confidence >= 0.35", {"confidence": 0.2}) is False

    def test_and(self):
        assert _eval_expr("x > 1 and y < 10", {"x": 5, "y": 3}) is True
        assert _eval_expr("x > 1 and y < 10", {"x": 0, "y": 3}) is False

    def test_or(self):
        assert _eval_expr("x > 10 or y > 10", {"x": 5, "y": 15}) is True
        assert _eval_expr("x > 10 or y > 10", {"x": 5, "y": 5}) is False

    def test_missing_field_returns_none(self):
        assert _eval_expr("x == None", {}) is True

    def test_missing_field_comparison_is_safe(self):
        # Comparing None > 5 should return False, not crash
        assert _eval_expr("x > 5", {}) is False

    def test_invalid_expr_raises(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            _eval_expr("not a valid expression!!!", {})


# ======================================================================
# Edge
# ======================================================================


class TestEdge:
    def test_unconditional(self):
        e = Edge(source="a", target="b")
        assert e.evaluate(AgentState()) is True

    def test_callable_condition(self):
        e = Edge(source="a", target="b", condition=lambda s: s.get("go", False))
        assert e.evaluate(AgentState({"go": True})) is True
        assert e.evaluate(AgentState({"go": False})) is False

    def test_string_condition(self):
        e = Edge(source="a", target="b", condition="score >= 0.5")
        assert e.evaluate(AgentState({"score": 0.8})) is True
        assert e.evaluate(AgentState({"score": 0.2})) is False

    def test_to_dict_string_condition(self):
        e = Edge(source="a", target="b", condition="x > 5", label="high")
        d = e.to_dict()
        assert d["source"] == "a"
        assert d["target"] == "b"
        assert d["condition"] == "x > 5"
        assert d["label"] == "high"

    def test_to_dict_callable_condition(self):
        e = Edge(source="a", target="b", condition=lambda s: True)
        d = e.to_dict()
        assert d["condition"].startswith("<callable:")


# ======================================================================
# Node types
# ======================================================================


class TestPassthroughNode:
    def test_passes_state_unchanged(self):
        node = PassthroughNode()
        s = AgentState({"x": 1})
        result = node.execute(s)
        assert result is s
        assert result["x"] == 1

    def test_node_type(self):
        assert PassthroughNode.node_type == "passthrough"


class TestFunctionNode:
    def test_wraps_callable(self):
        def add_greeting(s):
            s["greeting"] = "hello"
            return s

        node = FunctionNode(add_greeting)
        result = node.execute(AgentState())
        assert result["greeting"] == "hello"

    def test_normalises_plain_dict(self):
        node = FunctionNode(lambda s: {"key": "val"})
        result = node.execute(AgentState())
        assert isinstance(result, AgentState)
        assert result["key"] == "val"

    def test_label_from_name(self):
        def my_func(s):
            return s

        node = FunctionNode(my_func)
        assert node.label == "my_func"

    def test_to_dict(self):
        node = FunctionNode(lambda s: s, label="test")
        d = node.to_dict()
        assert d["type"] == "function"
        assert d["label"] == "test"


class TestTransformNode:
    def test_sets_defaults(self):
        node = TransformNode(defaults={"model": "gpt-4o", "top_k": 10})
        result = node.execute(AgentState({"query": "hi"}))
        assert result["model"] == "gpt-4o"
        assert result["top_k"] == 10
        assert result["query"] == "hi"

    def test_roundtrip(self):
        node = TransformNode(defaults={"a": 1})
        restored = TransformNode.from_dict(node.to_dict())
        assert restored.defaults == {"a": 1}


class TestResponseNode:
    def test_fixed_message(self):
        node = ResponseNode(message="No results found.")
        result = node.execute(AgentState())
        assert result["response"] == "No results found."

    def test_template(self):
        node = ResponseNode(template="Hello {name}, you asked: {query}")
        result = node.execute(AgentState({"name": "Alice", "query": "weather"}))
        assert result["response"] == "Hello Alice, you asked: weather"

    def test_passthrough_when_no_message(self):
        node = ResponseNode()
        s = AgentState({"x": 1})
        result = node.execute(s)
        assert "response" not in result
        assert result["x"] == 1

    def test_custom_output_field(self):
        node = ResponseNode(message="done", output_field="answer")
        result = node.execute(AgentState())
        assert result["answer"] == "done"


class TestGuardNode:
    def test_passes_above_threshold(self):
        node = GuardNode(threshold=0.5)
        result = node.execute(AgentState({"confidence": 0.8}))
        assert result["guard_passed"] is True
        assert result["guard_score"] == 0.8
        assert result["guard_threshold"] == 0.5

    def test_fails_below_threshold(self):
        node = GuardNode(threshold=0.5)
        result = node.execute(AgentState({"confidence": 0.2}))
        assert result["guard_passed"] is False

    def test_passes_at_threshold(self):
        node = GuardNode(threshold=0.5)
        result = node.execute(AgentState({"confidence": 0.5}))
        assert result["guard_passed"] is True

    def test_custom_score_field(self):
        node = GuardNode(threshold=0.3, score_field="relevance")
        result = node.execute(AgentState({"relevance": 0.1}))
        assert result["guard_passed"] is False

    def test_missing_score_defaults_zero(self):
        node = GuardNode(threshold=0.5)
        result = node.execute(AgentState())
        assert result["guard_passed"] is False
        assert result["guard_score"] == 0.0

    def test_roundtrip(self):
        node = GuardNode(threshold=0.7, score_field="sim")
        restored = GuardNode.from_dict(node.to_dict())
        assert restored.threshold == 0.7
        assert restored.score_field == "sim"


class TestMapNode:
    def test_maps_items(self):
        node = MapNode(fn=lambda x: x * 2, input_field="nums", output_field="doubled")
        result = node.execute(AgentState({"nums": [1, 2, 3]}))
        assert result["doubled"] == [2, 4, 6]

    def test_empty_list(self):
        node = MapNode(fn=lambda x: x)
        result = node.execute(AgentState())
        assert result["results"] == []


class TestFilterNode:
    def test_filters_items(self):
        node = FilterNode(
            predicate=lambda x: x > 3, input_field="nums", output_field="big"
        )
        result = node.execute(AgentState({"nums": [1, 2, 5, 8]}))
        assert result["big"] == [5, 8]


class TestLLMNode:
    def test_calls_fn_and_sets_output(self):
        def mock_llm(prompt: str) -> str:
            return f"Answer to: {prompt}"

        node = LLMNode(
            call_fn=mock_llm,
            prompt_template="Q: {query}",
            output_field="answer",
        )
        result = node.execute(AgentState({"query": "what is RAG?"}))
        assert result["answer"] == "Answer to: Q: what is RAG?"


# ======================================================================
# Node registry
# ======================================================================


class TestNodeRegistry:
    def test_all_builtin_types_registered(self):
        expected = {
            "passthrough", "function", "transform", "response",
            "map", "filter", "guard", "retriever", "llm",
        }
        assert expected.issubset(set(NODE_REGISTRY.keys()))


# ======================================================================
# AgentGraph — construction
# ======================================================================


class TestGraphConstruction:
    def test_fluent_api(self):
        g = (
            AgentGraph("test")
            .add_node("a", PassthroughNode())
            .add_node("b", PassthroughNode())
            .add_edge("a", "b")
            .set_entry("a")
        )
        assert isinstance(g, AgentGraph)
        assert g.node_names == ["a", "b"]
        assert len(g.edges) == 1

    def test_duplicate_node_raises(self):
        g = AgentGraph("test").add_node("a", PassthroughNode())
        with pytest.raises(ValueError, match="Duplicate"):
            g.add_node("a", PassthroughNode())

    def test_non_node_raises(self):
        g = AgentGraph("test")
        with pytest.raises(TypeError, match="BaseNode"):
            g.add_node("a", "not a node")  # type: ignore[arg-type]

    def test_entry_must_exist(self):
        g = AgentGraph("test")
        with pytest.raises(ValueError, match="not found"):
            g.set_entry("nonexistent")

    def test_repr(self):
        g = AgentGraph("demo").add_node("a", PassthroughNode()).set_entry("a")
        r = repr(g)
        assert "demo" in r
        assert "nodes=1" in r


# ======================================================================
# AgentGraph — validation
# ======================================================================


class TestGraphValidation:
    def test_valid_graph(self):
        g = (
            AgentGraph("ok")
            .add_node("a", PassthroughNode())
            .add_node("b", PassthroughNode())
            .add_edge("a", "b")
            .set_entry("a")
        )
        assert g.validate() == []

    def test_no_entry_error(self):
        g = AgentGraph("bad").add_node("a", PassthroughNode())
        errors = g.validate()
        assert any("entry" in e.lower() for e in errors)

    def test_missing_edge_source(self):
        g = (
            AgentGraph("bad")
            .add_node("a", PassthroughNode())
            .add_edge("x", "a")
            .set_entry("a")
        )
        errors = g.validate()
        assert any("x" in e for e in errors)

    def test_missing_edge_target(self):
        g = (
            AgentGraph("bad")
            .add_node("a", PassthroughNode())
            .add_edge("a", "z")
            .set_entry("a")
        )
        errors = g.validate()
        assert any("z" in e for e in errors)

    def test_cycle_detection(self):
        g = (
            AgentGraph("cycle")
            .add_node("a", PassthroughNode())
            .add_node("b", PassthroughNode())
            .add_edge("a", "b")
            .add_edge("b", "a")
            .set_entry("a")
        )
        errors = g.validate()
        assert any("cycle" in e.lower() for e in errors)


# ======================================================================
# AgentGraph — execution
# ======================================================================


class TestGraphExecution:
    def test_linear_graph(self):
        """A → B → C executes all three in order."""
        log: list[str] = []

        def step(name):
            def _fn(s):
                log.append(name)
                s[name] = True
                return s
            return _fn

        g = (
            AgentGraph("linear")
            .add_node("a", FunctionNode(step("a")))
            .add_node("b", FunctionNode(step("b")))
            .add_node("c", FunctionNode(step("c")))
            .add_edge("a", "b")
            .add_edge("b", "c")
            .set_entry("a")
        )
        result = g.run()
        assert result.success
        assert result.nodes_executed == 3
        assert log == ["a", "b", "c"]
        assert result.output["a"] is True
        assert result.output["c"] is True

    def test_conditional_branching_string(self):
        """Guard → synth (if pass) or fallback (if fail), string conditions."""
        g = (
            AgentGraph("branch")
            .add_node("guard", GuardNode(threshold=0.5))
            .add_node("synth", ResponseNode(message="synthesised"))
            .add_node("fallback", ResponseNode(message="no data"))
            .add_edge("guard", "synth", condition="guard_passed == True")
            .add_edge("guard", "fallback", condition="guard_passed == False")
            .set_entry("guard")
        )

        # High confidence → synth
        r1 = g.run({"confidence": 0.8})
        assert r1.success
        assert r1.output["response"] == "synthesised"
        assert r1.nodes_executed == 2

        # Low confidence → fallback
        r2 = g.run({"confidence": 0.1})
        assert r2.success
        assert r2.output["response"] == "no data"
        assert r2.nodes_executed == 2

    def test_conditional_branching_callable(self):
        """Same branching test but with callable conditions."""
        g = (
            AgentGraph("branch-fn")
            .add_node("guard", GuardNode(threshold=0.5))
            .add_node("yes", ResponseNode(message="yes"))
            .add_node("no", ResponseNode(message="no"))
            .add_edge("guard", "yes", condition=lambda s: s.get("guard_passed"))
            .add_edge("guard", "no", condition=lambda s: not s.get("guard_passed"))
            .set_entry("guard")
        )
        assert g.run({"confidence": 1.0}).output["response"] == "yes"
        assert g.run({"confidence": 0.0}).output["response"] == "no"

    def test_terminal_node(self):
        """A node with no outgoing edges stops execution."""
        g = (
            AgentGraph("terminal")
            .add_node("only", PassthroughNode())
            .set_entry("only")
        )
        r = g.run({"x": 1})
        assert r.success
        assert r.nodes_executed == 1
        assert r.output["x"] == 1

    def test_dead_end_no_matching_condition(self):
        """If no outgoing edge's condition matches, execution stops."""
        g = (
            AgentGraph("dead")
            .add_node("a", PassthroughNode())
            .add_node("b", PassthroughNode())
            .add_edge("a", "b", condition="x > 100")
            .set_entry("a")
        )
        r = g.run({"x": 1})
        assert r.success  # not an error, just no next node
        assert r.nodes_executed == 1

    def test_node_error_is_caught(self):
        """A node that raises an exception produces an error trace."""
        def boom(s):
            raise RuntimeError("kaboom")

        g = (
            AgentGraph("err")
            .add_node("fail", FunctionNode(boom))
            .set_entry("fail")
        )
        r = g.run()
        assert not r.success
        assert r.error is not None
        assert "kaboom" in r.error
        assert r.nodes_executed == 1
        assert r.trace[0].error is not None

    def test_max_steps_limit(self):
        """Execution stops when max_steps is reached."""
        # This shouldn't normally happen with cycle detection,
        # but max_steps is a safety net.
        g = (
            AgentGraph("long")
            .add_node("a", PassthroughNode())
            .add_node("b", PassthroughNode())
            .add_node("c", PassthroughNode())
            .add_edge("a", "b")
            .add_edge("b", "c")
            .set_entry("a")
        )
        r = g.run(max_steps=2)
        assert r.nodes_executed == 2  # stopped before c

    def test_invalid_graph_raises(self):
        """Running an invalid graph raises ValueError."""
        g = AgentGraph("bad")  # no entry, no nodes
        with pytest.raises(ValueError, match="Invalid graph"):
            g.run()

    def test_initial_state_dict(self):
        """Plain dict is accepted as initial state."""
        g = (
            AgentGraph("dict-init")
            .add_node("a", PassthroughNode())
            .set_entry("a")
        )
        r = g.run({"key": "val"})
        assert r.output["key"] == "val"

    def test_initial_state_none(self):
        """None initial state starts with empty state."""
        g = (
            AgentGraph("none-init")
            .add_node("a", TransformNode(defaults={"x": 1}))
            .set_entry("a")
        )
        r = g.run()
        assert r.output["x"] == 1


# ======================================================================
# AgentGraph — traces
# ======================================================================


class TestGraphTraces:
    def test_trace_per_node(self):
        g = (
            AgentGraph("traced")
            .add_node("a", PassthroughNode())
            .add_node("b", PassthroughNode())
            .add_edge("a", "b")
            .set_entry("a")
        )
        r = g.run({"key": "val"})
        assert len(r.trace) == 2
        assert r.trace[0].node_name == "a"
        assert r.trace[1].node_name == "b"

    def test_trace_has_timing(self):
        g = (
            AgentGraph("timed")
            .add_node("a", PassthroughNode())
            .set_entry("a")
        )
        r = g.run()
        t = r.trace[0]
        assert t.duration_ms >= 0
        assert t.started_at <= t.ended_at
        assert r.total_ms >= 0

    def test_trace_has_node_type(self):
        g = (
            AgentGraph("typed")
            .add_node("a", GuardNode(threshold=0.5))
            .set_entry("a")
        )
        r = g.run({"confidence": 0.8})
        assert r.trace[0].node_type == "guard"

    def test_trace_input_output_keys(self):
        g = (
            AgentGraph("keys")
            .add_node("a", TransformNode(defaults={"new_key": 42}))
            .set_entry("a")
        )
        r = g.run({"existing": "data"})
        t = r.trace[0]
        assert "existing" in t.input_keys
        assert "new_key" in t.output_keys


# ======================================================================
# AgentResult
# ======================================================================


class TestAgentResult:
    def test_to_dict(self):
        r = AgentResult(
            output=AgentState({"answer": "42"}),
            trace=[],
            total_ms=5.123,
            nodes_executed=2,
            graph_name="test",
            success=True,
        )
        d = r.to_dict()
        assert d["graph_name"] == "test"
        assert d["success"] is True
        assert d["total_ms"] == 5.123
        assert d["nodes_executed"] == 2
        assert d["output"]["answer"] == "42"

    def test_error_result(self):
        r = AgentResult(
            output=AgentState(),
            trace=[],
            total_ms=1.0,
            nodes_executed=1,
            graph_name="err",
            success=False,
            error="RuntimeError: boom",
        )
        d = r.to_dict()
        assert d["success"] is False
        assert "boom" in d["error"]


# ======================================================================
# Serialization
# ======================================================================


class TestSerialization:
    def test_roundtrip_simple_graph(self):
        """Serialize → deserialize produces an equivalent graph."""
        g = (
            AgentGraph("roundtrip", description="test graph")
            .add_node("start", TransformNode(defaults={"x": 1}))
            .add_node("guard", GuardNode(threshold=0.5))
            .add_node("end", ResponseNode(message="done"))
            .add_edge("start", "guard")
            .add_edge("guard", "end", condition="guard_passed == True")
            .set_entry("start")
        )
        d = g.to_dict()
        g2 = AgentGraph.from_dict(d)

        assert g2.name == "roundtrip"
        assert g2.description == "test graph"
        assert g2.node_names == ["start", "guard", "end"]
        assert len(g2.edges) == 2

        # Run the deserialized graph
        r = g2.run({"confidence": 0.8})
        assert r.success
        assert r.output["response"] == "done"

    def test_callable_condition_placeholder(self):
        """Callable conditions serialize as placeholders and deserialize as None."""
        g = (
            AgentGraph("callable")
            .add_node("a", PassthroughNode())
            .add_node("b", PassthroughNode())
            .add_edge("a", "b", condition=lambda s: True)
            .set_entry("a")
        )
        d = g.to_dict()
        edge_d = d["edges"][0]
        assert edge_d["condition"].startswith("<callable:")

        # Deserialize — callable condition becomes None (unconditional)
        g2 = AgentGraph.from_dict(d)
        assert g2.edges[0].condition is None

    def test_unknown_node_type_raises(self):
        bad = {
            "name": "bad",
            "entry": "x",
            "nodes": {"x": {"type": "nonexistent_type_xyz", "name": "x"}},
            "edges": [],
        }
        with pytest.raises(ValueError, match="Unknown node type"):
            AgentGraph.from_dict(bad)

    def test_to_dict_structure(self):
        g = (
            AgentGraph("struct")
            .add_node("a", GuardNode(threshold=0.7))
            .set_entry("a")
        )
        d = g.to_dict()
        assert d["name"] == "struct"
        assert d["entry"] == "a"
        assert "a" in d["nodes"]
        assert d["nodes"]["a"]["type"] == "guard"
        assert d["nodes"]["a"]["threshold"] == 0.7
        assert d["nodes"]["a"]["name"] == "a"


# ======================================================================
# Integration — RAG-like pipeline
# ======================================================================


class TestRAGPipeline:
    """End-to-end test simulating a simplified RAG agent graph."""

    def test_full_rag_pipeline(self):
        """Simulates: embed → retrieve → guard → synthesize/fallback."""

        def mock_retrieve(s):
            query = s.get("query", "")
            if "attention" in query.lower():
                s["results"] = [{"text": "Multi-head attention...", "score": 0.85}]
                s["confidence"] = 0.85
            else:
                s["results"] = []
                s["confidence"] = 0.0
            return s

        def mock_synthesize(s):
            context = s["results"][0]["text"] if s.get("results") else ""
            s["answer"] = f"Based on: {context}"
            return s

        graph = (
            AgentGraph("rag-pipeline")
            .add_node("retrieve", FunctionNode(mock_retrieve, label="retriever"))
            .add_node("guard", GuardNode(threshold=0.35))
            .add_node("synthesize", FunctionNode(mock_synthesize, label="synthesizer"))
            .add_node("fallback", ResponseNode(message="I don't have enough context."))
            .add_edge("retrieve", "guard")
            .add_edge("guard", "synthesize", condition="guard_passed == True")
            .add_edge("guard", "fallback", condition="guard_passed == False")
            .set_entry("retrieve")
        )

        # Good query → synthesis path
        r1 = graph.run({"query": "what is multi-head attention?"})
        assert r1.success
        assert r1.nodes_executed == 3
        assert "Multi-head attention" in r1.output["answer"]
        # Verify trace order
        assert [t.node_name for t in r1.trace] == ["retrieve", "guard", "synthesize"]

        # Bad query → fallback path
        r2 = graph.run({"query": "recipe for chocolate cake"})
        assert r2.success
        assert r2.nodes_executed == 3
        assert r2.output.get("response") == "I don't have enough context."
        assert [t.node_name for t in r2.trace] == ["retrieve", "guard", "fallback"]

    def test_pipeline_with_llm_node(self):
        """LLMNode wraps a mock LLM callable."""
        calls: list[str] = []

        def mock_llm(prompt: str) -> str:
            calls.append(prompt)
            return f"LLM says: {prompt[:20]}..."

        graph = (
            AgentGraph("llm-test")
            .add_node("prepare", TransformNode(defaults={"query": "test question"}))
            .add_node("llm", LLMNode(
                call_fn=mock_llm,
                prompt_template="Answer this: {query}",
                output_field="answer",
            ))
            .add_edge("prepare", "llm")
            .set_entry("prepare")
        )
        r = graph.run()
        assert r.success
        assert len(calls) == 1
        assert "Answer this: test question" in calls[0]
        assert r.output["answer"].startswith("LLM says:")
