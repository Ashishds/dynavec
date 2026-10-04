"""Agent orchestration engine for dynavec.

Build directed-graph agent workflows with conditional routing,
built-in RAG primitives, and full telemetry integration.

Example::

    from dynavec.agents import AgentGraph, AgentState
    from dynavec.agents.nodes import FunctionNode, GuardNode

    graph = (
        AgentGraph("my-rag-agent")
        .add_node("retrieve", FunctionNode(my_retriever))
        .add_node("guard", GuardNode(threshold=0.35))
        .add_node("respond", FunctionNode(my_responder))
        .add_edge("retrieve", "guard")
        .add_edge("guard", "respond", condition="confidence >= 0.35")
        .set_entry("retrieve")
    )

    result = graph.run({"query": "what is attention?"})
"""

from __future__ import annotations

from .base import AgentResult, AgentState, Edge, NodeTrace
from .graph import AgentGraph
from .testing import (
    AssertionResult,
    BaseAssertion,
    ContainsAssertion,
    ExactMatchAssertion,
    ExpressionAssertion,
    MaxLatencyAssertion,
    NodeVisitedAssertion,
    RagasMetricAssertion,
    TestCase,
    TestCaseResult,
    TestRunner,
    TestSuite,
    TestSuiteResult,
)

__all__ = [
    "AgentGraph",
    "AgentResult",
    "AgentState",
    "AssertionResult",
    "BaseAssertion",
    "ContainsAssertion",
    "Edge",
    "ExactMatchAssertion",
    "ExpressionAssertion",
    "MaxLatencyAssertion",
    "NodeTrace",
    "NodeVisitedAssertion",
    "RagasMetricAssertion",
    "TestCase",
    "TestCaseResult",
    "TestRunner",
    "TestSuite",
    "TestSuiteResult",
]

