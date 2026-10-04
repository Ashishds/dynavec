"""Core types for the agent orchestration engine.

This module defines the foundational types shared across the agents
package: state, edges, traces, results, the abstract node base class,
the node registry, and the safe expression evaluator.
"""

from __future__ import annotations

import ast
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Node registry — populated by concrete node classes in nodes.py
# ---------------------------------------------------------------------------

NODE_REGISTRY: dict[str, type[BaseNode]] = {}


# ---------------------------------------------------------------------------
# AgentState
# ---------------------------------------------------------------------------


class AgentState(dict):
    """Mutable state dictionary that flows through the agent graph.

    Behaves like a regular ``dict`` with convenience methods for common
    RAG pipeline patterns.  Every node in the graph receives the state,
    may mutate it, and returns it.
    """

    def set(self, key: str, value: Any) -> AgentState:
        """Set a key and return *self* for chaining in lambdas."""
        self[key] = value
        return self


# ---------------------------------------------------------------------------
# BaseNode (abstract)
# ---------------------------------------------------------------------------


class BaseNode(ABC):
    """Abstract base class for all agent graph nodes.

    Subclasses must implement :meth:`execute` and set a class-level
    ``node_type`` string used for serialization.
    """

    node_type: str = "base"

    @abstractmethod
    def execute(self, state: AgentState) -> AgentState:
        """Process the state and return the (possibly modified) state.

        Implementations may read from and write to *state*.  The returned
        object is passed to the next node(s) in the graph.
        """
        ...

    def to_dict(self) -> dict:
        """Serialize this node's configuration for JSON / ReactFlow."""
        return {"type": self.node_type}

    @classmethod
    def from_dict(cls, data: dict) -> BaseNode:
        """Deserialize a node from a JSON-compatible dict."""
        return cls()



# ---------------------------------------------------------------------------
# Edge
# ---------------------------------------------------------------------------


@dataclass
class Edge:
    """Directed edge between two nodes, optionally gated by a condition.

    Conditions can be:

    * ``None`` — always taken (unconditional)
    * A callable ``(AgentState) -> bool``
    * A string expression like ``"confidence >= 0.35"``
    """

    source: str
    target: str
    condition: Callable[[AgentState], bool] | str | None = None
    label: str = ""

    def evaluate(self, state: AgentState) -> bool:
        """Return ``True`` if this edge should be followed."""
        if self.condition is None:
            return True
        if callable(self.condition):
            return bool(self.condition(state))
        if isinstance(self.condition, str):
            return _eval_expr(self.condition, state)
        raise TypeError(f"Unsupported condition type: {type(self.condition)}")

    def to_dict(self) -> dict:
        """Serialize for JSON.  Callables become descriptive strings."""
        d: dict[str, Any] = {"source": self.source, "target": self.target}
        if self.label:
            d["label"] = self.label
        if isinstance(self.condition, str):
            d["condition"] = self.condition
        elif self.condition is not None:
            d["condition"] = f"<callable:{getattr(self.condition, '__name__', 'fn')}>"
        return d


# ---------------------------------------------------------------------------
# Trace / Result
# ---------------------------------------------------------------------------


@dataclass
class NodeTrace:
    """Execution record for a single node within a graph run."""

    node_name: str
    node_type: str
    started_at: float
    ended_at: float
    duration_ms: float
    input_keys: list[str] = field(default_factory=list)
    output_keys: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "node_name": self.node_name,
            "node_type": self.node_type,
            "duration_ms": round(self.duration_ms, 3),
            "input_keys": self.input_keys,
            "output_keys": self.output_keys,
        }
        if self.error:
            d["error"] = self.error
        return d


@dataclass
class AgentResult:
    """Result of executing an agent graph."""

    output: AgentState
    trace: list[NodeTrace]
    total_ms: float
    nodes_executed: int
    graph_name: str
    success: bool = True
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "graph_name": self.graph_name,
            "success": self.success,
            "total_ms": round(self.total_ms, 3),
            "nodes_executed": self.nodes_executed,
            "trace": [t.to_dict() for t in self.trace],
            "output": dict(self.output),
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Safe expression evaluator (no eval / exec)
# ---------------------------------------------------------------------------

_COMPARE_RE = re.compile(r"^([\w][\w.]*)\s*(==|!=|>=|<=|>|<)\s*(.+)$")


def _eval_expr(expr: str, state: dict) -> bool:
    """Safely evaluate a simple comparison expression against state.

    Supports::

        field == value       field != value
        field > value        field >= value
        field < value        field <= value
        expr and expr        expr or expr

    Values are parsed with :func:`ast.literal_eval` (strings, numbers,
    bools, ``None``).  No arbitrary code execution is possible.
    """
    expr = expr.strip()

    # Handle 'or' (lowest precedence, split first)
    if " or " in expr:
        left, right = expr.split(" or ", 1)
        return _eval_expr(left, state) or _eval_expr(right, state)

    # Handle 'and'
    if " and " in expr:
        left, right = expr.split(" and ", 1)
        return _eval_expr(left, state) and _eval_expr(right, state)

    m = _COMPARE_RE.match(expr)
    if not m:
        raise ValueError(f"Cannot parse condition expression: {expr!r}")

    field_name, op, raw_value = m.group(1), m.group(2), m.group(3).strip()

    # Resolve dotted field access:  "result.score" → state["result"]["score"]
    actual: Any = state
    for part in field_name.split("."):
        if isinstance(actual, dict):
            actual = actual.get(part)
        else:
            actual = getattr(actual, part, None)

    # Parse expected value safely
    try:
        expected = ast.literal_eval(raw_value)
    except (ValueError, SyntaxError) as exc:
        raise ValueError(
            f"Cannot parse value {raw_value!r} in condition: {exc}"
        ) from exc

    _ops: dict[str, Callable[[Any, Any], bool]] = {
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        ">": lambda a, b: a is not None and a > b,
        ">=": lambda a, b: a is not None and a >= b,
        "<": lambda a, b: a is not None and a < b,
        "<=": lambda a, b: a is not None and a <= b,
    }
    return _ops[op](actual, expected)
