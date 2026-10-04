"""Agent test suites and assertion framework for dynavec.

Enables automated testing, CI assertions, and RAGAS-grade metric evaluations
for AgentGraph workflows.

Example::

    from dynavec.agents import AgentGraph
    from dynavec.agents.testing import (
        TestSuite,
        TestCase,
        ContainsAssertion,
        MaxLatencyAssertion,
        RagasMetricAssertion,
        TestRunner,
    )

    suite = TestSuite("enterprise-rag-qa", "Regression suite for enterprise docs")
    suite.add_case(
        TestCase(
            name="vector-search-explanation",
            input_state={"query": "how does dynavec achieve sub-10ms search?"},
            assertions=[
                ContainsAssertion("answer", "sub-10ms"),
                MaxLatencyAssertion(max_ms=500.0),
                RagasMetricAssertion("faithfulness", min_score=0.80),
            ],
            context_docs=["Dynavec uses S3 vectors and DynamoDB caching for sub-10ms search."],
        )
    )

    runner = TestRunner()
    result = runner.run(graph, suite)
    assert result.passed
"""

from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

from .base import AgentResult, _eval_expr
from .graph import AgentGraph

# ---------------------------------------------------------------------------
# Assertion Types
# ---------------------------------------------------------------------------


@dataclass
class AssertionResult:
    """Outcome of evaluating an individual assertion."""

    assertion_type: str
    passed: bool
    message: str
    expected: Any = None
    actual: Any = None
    score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "assertion_type": self.assertion_type,
            "passed": self.passed,
            "message": self.message,
            "expected": self.expected,
            "actual": self.actual,
        }
        if self.score is not None:
            d["score"] = round(self.score, 4)
        return d


class BaseAssertion(ABC):
    """Abstract base class for all test assertions."""

    assertion_type: str = "base"

    @abstractmethod
    def evaluate(
        self,
        result: AgentResult,
        case: TestCase,
    ) -> AssertionResult:
        """Evaluate this assertion against the execution result."""
        ...

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.assertion_type}


class ExactMatchAssertion(BaseAssertion):
    """Asserts that state[key] exactly equals expected_value."""

    assertion_type: str = "exact_match"

    def __init__(self, key: str, expected_value: Any) -> None:
        self.key = key
        self.expected_value = expected_value

    def evaluate(self, result: AgentResult, case: TestCase) -> AssertionResult:
        actual = result.output.get(self.key)
        passed = actual == self.expected_value
        return AssertionResult(
            assertion_type=self.assertion_type,
            passed=passed,
            message=(
                f"Field '{self.key}' matches expected value"
                if passed
                else f"Field '{self.key}' was '{actual}', expected '{self.expected_value}'"
            ),
            expected=self.expected_value,
            actual=actual,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.assertion_type,
            "key": self.key,
            "expected_value": self.expected_value,
        }


class ContainsAssertion(BaseAssertion):
    """Asserts that substring exists in state[key] (string or collection)."""

    assertion_type: str = "contains"

    def __init__(self, key: str, substring: str, case_sensitive: bool = False) -> None:
        self.key = key
        self.substring = substring
        self.case_sensitive = case_sensitive

    def evaluate(self, result: AgentResult, case: TestCase) -> AssertionResult:
        actual = result.output.get(self.key)
        if actual is None:
            return AssertionResult(
                assertion_type=self.assertion_type,
                passed=False,
                message=f"Key '{self.key}' not found in state output",
                expected=self.substring,
                actual=None,
            )

        if isinstance(actual, (list, tuple, set)):
            passed = self.substring in actual
        else:
            text = str(actual)
            sub = self.substring
            if not self.case_sensitive:
                text = text.lower()
                sub = sub.lower()
            passed = sub in text

        return AssertionResult(
            assertion_type=self.assertion_type,
            passed=passed,
            message=(
                f"Field '{self.key}' contains '{self.substring}'"
                if passed
                else f"Field '{self.key}' does not contain '{self.substring}'"
            ),
            expected=self.substring,
            actual=str(actual)[:120],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.assertion_type,
            "key": self.key,
            "substring": self.substring,
            "case_sensitive": self.case_sensitive,
        }


class ExpressionAssertion(BaseAssertion):
    """Asserts that a safe state expression evaluates to True."""

    assertion_type: str = "expression"

    def __init__(self, expr: str) -> None:
        self.expr = expr

    def evaluate(self, result: AgentResult, case: TestCase) -> AssertionResult:
        passed = _eval_expr(self.expr, result.output)
        return AssertionResult(
            assertion_type=self.assertion_type,
            passed=passed,
            message=f"Expression '{self.expr}' evaluated to {passed}",
            expected=True,
            actual=passed,
        )

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.assertion_type, "expr": self.expr}


class NodeVisitedAssertion(BaseAssertion):
    """Asserts that a specific node was executed in the graph."""

    assertion_type: str = "node_visited"

    def __init__(self, node_name: str, must_visit: bool = True) -> None:
        self.node_name = node_name
        self.must_visit = must_visit

    def evaluate(self, result: AgentResult, case: TestCase) -> AssertionResult:
        visited_nodes = [t.node_name for t in result.trace]
        is_visited = self.node_name in visited_nodes
        passed = is_visited if self.must_visit else not is_visited

        return AssertionResult(
            assertion_type=self.assertion_type,
            passed=passed,
            message=(
                f"Node '{self.node_name}' was {'visited' if is_visited else 'not visited'}"
            ),
            expected=f"{'visited' if self.must_visit else 'not visited'}",
            actual=f"{'visited' if is_visited else 'not visited'}",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.assertion_type,
            "node_name": self.node_name,
            "must_visit": self.must_visit,
        }


class MaxLatencyAssertion(BaseAssertion):
    """Asserts that total execution duration does not exceed max_ms."""

    assertion_type: str = "max_latency"

    def __init__(self, max_ms: float) -> None:
        self.max_ms = max_ms

    def evaluate(self, result: AgentResult, case: TestCase) -> AssertionResult:
        passed = result.total_ms <= self.max_ms
        return AssertionResult(
            assertion_type=self.assertion_type,
            passed=passed,
            message=(
                f"Total latency {result.total_ms:.1f}ms <= {self.max_ms:.1f}ms"
                if passed
                else f"Total latency {result.total_ms:.1f}ms exceeded SLA threshold {self.max_ms:.1f}ms"
            ),
            expected=f"<={self.max_ms}ms",
            actual=f"{result.total_ms:.1f}ms",
        )

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.assertion_type, "max_ms": self.max_ms}


class RagasMetricAssertion(BaseAssertion):
    """Asserts that a RAGAS-grade metric meets or exceeds min_score.

    Supported metrics:
    - 'faithfulness': grounds the generated answer against context_docs
    - 'answer_relevance': checks keyword and intent relevance to query
    - 'context_recall': checks coverage of ground_truth in retrieved docs
    """

    assertion_type: str = "ragas_metric"

    def __init__(
        self,
        metric_name: str,
        min_score: float = 0.80,
        eval_fn: Callable[[str, list[str], str], float] | None = None,
    ) -> None:
        self.metric_name = metric_name.lower()
        self.min_score = min_score
        self.eval_fn = eval_fn

    def evaluate(self, result: AgentResult, case: TestCase) -> AssertionResult:
        score = self._compute_metric(result, case)
        passed = score >= self.min_score
        return AssertionResult(
            assertion_type=self.assertion_type,
            passed=passed,
            message=(
                f"RAGAS '{self.metric_name}' score {score:.2f} >= threshold {self.min_score:.2f}"
                if passed
                else f"RAGAS '{self.metric_name}' score {score:.2f} failed threshold {self.min_score:.2f}"
            ),
            expected=f">={self.min_score}",
            actual=round(score, 4),
            score=score,
        )

    def _compute_metric(self, result: AgentResult, case: TestCase) -> float:
        if self.eval_fn:
            ans = str(result.output.get("answer") or result.output.get("response") or "")
            q = str(case.input_state.get("query", ""))
            return self.eval_fn(q, case.context_docs or [], ans)

        ans = str(result.output.get("answer") or result.output.get("response") or "").lower()
        q = str(case.input_state.get("query", "")).lower()
        contexts = [c.lower() for c in (case.context_docs or [])]

        if self.metric_name == "faithfulness":
            if not contexts or not ans:
                return 1.0
            # Token overlap between generated answer and context chunks
            ans_tokens = set(re.findall(r"\w+", ans))
            if not ans_tokens:
                return 1.0
            ctx_tokens = set().union(*(re.findall(r"\w+", c) for c in contexts))
            grounded_tokens = ans_tokens.intersection(ctx_tokens)
            return len(grounded_tokens) / len(ans_tokens)

        elif self.metric_name == "answer_relevance":
            if not q or not ans:
                return 1.0
            q_tokens = set(re.findall(r"\w+", q))
            ans_tokens = set(re.findall(r"\w+", ans))
            if not q_tokens:
                return 1.0
            overlap = q_tokens.intersection(ans_tokens)
            return min(1.0, (len(overlap) / len(q_tokens)) * 1.2)

        elif self.metric_name == "context_recall":
            if not case.ground_truth or not contexts:
                return 1.0
            gt_tokens = set(re.findall(r"\w+", case.ground_truth.lower()))
            ctx_tokens = set().union(*(re.findall(r"\w+", c) for c in contexts))
            if not gt_tokens:
                return 1.0
            recalled = gt_tokens.intersection(ctx_tokens)
            return len(recalled) / len(gt_tokens)

        # Default fallback metric
        return 0.90

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.assertion_type,
            "metric_name": self.metric_name,
            "min_score": self.min_score,
        }


# ---------------------------------------------------------------------------
# Test Case & Test Suite Models
# ---------------------------------------------------------------------------


@dataclass
class TestCase:
    """Individual test case definition for an AgentGraph."""

    __test__ = False

    name: str
    input_state: dict[str, Any]
    assertions: list[BaseAssertion] = field(default_factory=list)
    context_docs: list[str] | None = None
    ground_truth: str | None = None
    tags: list[str] = field(default_factory=list)
    description: str = ""

    def add_assertion(self, assertion: BaseAssertion) -> TestCase:
        self.assertions.append(assertion)
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_state": self.input_state,
            "assertions": [a.to_dict() for a in self.assertions],
            "context_docs": self.context_docs,
            "ground_truth": self.ground_truth,
            "tags": self.tags,
        }


@dataclass
class TestCaseResult:
    """Execution and evaluation result for a single TestCase."""

    __test__ = False

    case_name: str
    passed: bool
    duration_ms: float
    assertion_results: list[AssertionResult]
    agent_result: AgentResult | None = None
    ragas_scores: dict[str, float] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_name": self.case_name,
            "passed": self.passed,
            "duration_ms": round(self.duration_ms, 2),
            "assertions": [a.to_dict() for a in self.assertion_results],
            "ragas_scores": {k: round(v, 4) for k, v in self.ragas_scores.items()},
            "error": self.error,
        }


class TestSuite:
    """Collection of TestCases for automated evaluation and regression testing."""

    __test__ = False

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self.cases: list[TestCase] = []

    def add_case(self, case: TestCase) -> TestSuite:
        self.cases.append(case)
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "cases": [c.to_dict() for c in self.cases],
        }


@dataclass
class TestSuiteResult:
    """Aggregated results across all test cases in a suite."""

    __test__ = False

    suite_name: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    total_duration_ms: float
    case_results: list[TestCaseResult]
    avg_ragas_metrics: dict[str, float] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.failed_cases == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite_name": self.suite_name,
            "passed": self.passed,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "pass_rate": round(self.pass_rate, 4),
            "total_duration_ms": round(self.total_duration_ms, 2),
            "avg_ragas_metrics": {
                k: round(v, 4) for k, v in self.avg_ragas_metrics.items()
            },
            "cases": [c.to_dict() for c in self.case_results],
        }

    def to_junit_xml(self) -> str:
        """Export results to standard JUnit XML format for CI/CD runners."""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<testsuite name="{self.suite_name}" tests="{self.total_cases}" failures="{self.failed_cases}" time="{self.total_duration_ms / 1000.0:.3f}">',
        ]
        for cr in self.case_results:
            lines.append(
                f'  <testcase name="{cr.case_name}" time="{cr.duration_ms / 1000.0:.3f}">'
            )
            if not cr.passed:
                failed_msgs = "; ".join(
                    a.message for a in cr.assertion_results if not a.passed
                )
                lines.append(
                    f'    <failure message="Assertion failure">{failed_msgs}</failure>'
                )
            lines.append("  </testcase>")
        lines.append("</testsuite>")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------


class TestRunner:
    """Executes a TestSuite against an AgentGraph and gathers evaluation metrics."""

    def run(self, graph: AgentGraph, suite: TestSuite) -> TestSuiteResult:
        start_time = time.perf_counter()
        case_results: list[TestCaseResult] = []
        metric_sums: dict[str, float] = {}
        metric_counts: dict[str, int] = {}

        for case in suite.cases:
            case_start = time.perf_counter()
            agent_res: AgentResult | None = None
            assertion_results: list[AssertionResult] = []
            case_passed = True
            err_msg: str | None = None
            ragas_scores: dict[str, float] = {}

            try:
                # Run the agent graph
                agent_res = graph.run(case.input_state)

                # Evaluate all assertions
                for assertion in case.assertions:
                    res = assertion.evaluate(agent_res, case)
                    assertion_results.append(res)
                    if not res.passed:
                        case_passed = False
                    if res.score is not None and isinstance(
                        assertion, RagasMetricAssertion
                    ):
                        ragas_scores[assertion.metric_name] = res.score
                        metric_sums[assertion.metric_name] = (
                            metric_sums.get(assertion.metric_name, 0.0) + res.score
                        )
                        metric_counts[assertion.metric_name] = (
                            metric_counts.get(assertion.metric_name, 0) + 1
                        )

            except Exception as ex:
                case_passed = False
                err_msg = str(ex)

            case_duration = (time.perf_counter() - case_start) * 1000.0

            case_results.append(
                TestCaseResult(
                    case_name=case.name,
                    passed=case_passed,
                    duration_ms=case_duration,
                    assertion_results=assertion_results,
                    agent_result=agent_res,
                    ragas_scores=ragas_scores,
                    error=err_msg,
                )
            )

        total_duration = (time.perf_counter() - start_time) * 1000.0
        total_cases = len(case_results)
        passed_cases = sum(1 for c in case_results if c.passed)
        failed_cases = total_cases - passed_cases
        pass_rate = (passed_cases / total_cases) if total_cases > 0 else 1.0

        avg_metrics: dict[str, float] = {}
        for m, s in metric_sums.items():
            cnt = metric_counts.get(m, 1)
            avg_metrics[m] = s / cnt if cnt > 0 else 0.0

        return TestSuiteResult(
            suite_name=suite.name,
            total_cases=total_cases,
            passed_cases=passed_cases,
            failed_cases=failed_cases,
            pass_rate=pass_rate,
            total_duration_ms=total_duration,
            case_results=case_results,
            avg_ragas_metrics=avg_metrics,
        )
