"""Agent graph engine — define, execute, and trace directed-graph workflows.

The :class:`AgentGraph` is the central orchestration primitive.  You
register named :class:`~dynavec.agents.base.BaseNode` instances, wire
them with edges (optionally conditional), set an entry point, and call
:meth:`run`.  The engine follows edges in order, evaluating conditions
against the live state, and produces an :class:`AgentResult` with a
full per-node execution trace.

Serialization
~~~~~~~~~~~~~
:meth:`AgentGraph.to_dict` produces a JSON-compatible dict that the
ReactFlow canvas can consume.  :meth:`AgentGraph.from_dict` reconstructs
the graph from that dict (string conditions only — callables serialize as
descriptive placeholders).
"""

from __future__ import annotations

import time
from typing import Any

# Force node registration by importing the module.
from . import nodes as _nodes  # noqa: F401
from .base import (
    NODE_REGISTRY,
    AgentResult,
    AgentState,
    BaseNode,
    Edge,
    NodeTrace,
)

_MAX_STEPS = 100  # hard ceiling to prevent infinite loops


class AgentGraph:
    """Directed graph of nodes with conditional edge routing.

    Nodes are named processing steps.  Edges connect them, optionally
    gated by conditions (callables or safe string expressions).
    Execution starts from the entry node and follows the first matching
    outgoing edge at each step.

    Example::

        graph = (
            AgentGraph("qa-pipeline")
            .add_node("search", FunctionNode(do_search))
            .add_node("answer", FunctionNode(do_answer))
            .add_edge("search", "answer")
            .set_entry("search")
        )
        result = graph.run({"query": "hello"})
    """

    def __init__(self, name: str, *, description: str = "") -> None:
        self.name = name
        self.description = description
        self._nodes: dict[str, BaseNode] = {}
        self._edges: list[Edge] = []
        self._entry: str | None = None

    # ----------------------------------------------------------------- build

    def add_node(self, name: str, node: BaseNode) -> AgentGraph:
        """Register a named node.  Returns *self* for fluent chaining."""
        if not isinstance(node, BaseNode):
            raise TypeError(
                f"Expected a BaseNode subclass, got {type(node).__name__}"
            )
        if name in self._nodes:
            raise ValueError(f"Duplicate node name: {name!r}")
        self._nodes[name] = node
        return self

    def add_edge(
        self,
        source: str,
        target: str,
        *,
        condition: Any | None = None,
        label: str = "",
    ) -> AgentGraph:
        """Connect two nodes with an optional condition.  Returns *self*."""
        self._edges.append(
            Edge(
                source=source,
                target=target,
                condition=condition,
                label=label,
            )
        )
        return self

    def set_entry(self, name: str) -> AgentGraph:
        """Designate the entry point of the graph.  Returns *self*."""
        if name not in self._nodes:
            raise ValueError(f"Entry node {name!r} not found in graph")
        self._entry = name
        return self

    @property
    def node_names(self) -> list[str]:
        """Ordered list of registered node names."""
        return list(self._nodes.keys())

    @property
    def edges(self) -> list[Edge]:
        """Copy of the edge list."""
        return list(self._edges)

    # -------------------------------------------------------------- validate

    def validate(self) -> list[str]:
        """Return a list of validation errors (empty list means valid)."""
        errors: list[str] = []

        if self._entry is None:
            errors.append("No entry node set (call .set_entry())")
        elif self._entry not in self._nodes:
            errors.append(f"Entry node {self._entry!r} not found")

        for edge in self._edges:
            if edge.source not in self._nodes:
                errors.append(f"Edge source {edge.source!r} not found")
            if edge.target not in self._nodes:
                errors.append(f"Edge target {edge.target!r} not found")

        # Cycle detection via DFS
        visited: set[str] = set()
        rec_stack: set[str] = set()
        adj: dict[str, list[str]] = {n: [] for n in self._nodes}
        for e in self._edges:
            if e.source in adj:
                adj[e.source].append(e.target)

        def _dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in adj.get(node, []):
                if neighbor in rec_stack:
                    errors.append(f"Cycle detected involving {neighbor!r}")
                elif neighbor not in visited:
                    _dfs(neighbor)
            rec_stack.discard(node)

        for n in self._nodes:
            if n not in visited:
                _dfs(n)

        return errors

    # ------------------------------------------------------------------- run

    def run(
        self,
        initial_state: AgentState | dict | None = None,
        *,
        recorder: Any | None = None,
        max_steps: int = _MAX_STEPS,
    ) -> AgentResult:
        """Execute the graph from the entry node.

        Parameters
        ----------
        initial_state:
            Starting state dict.
        recorder:
            Optional :class:`~dynavec.telemetry.TelemetryRecorder`.
        max_steps:
            Safety limit to prevent run-away execution.

        Returns
        -------
        AgentResult
            Contains the output state, per-node trace, and aggregate timing.
        """
        errors = self.validate()
        if errors:
            raise ValueError(f"Invalid graph: {'; '.join(errors)}")

        state = AgentState(initial_state or {})
        traces: list[NodeTrace] = []
        current: str | None = self._entry
        steps = 0
        t0 = time.perf_counter()

        while current is not None and steps < max_steps:
            steps += 1
            node = self._nodes[current]
            input_keys = list(state.keys())

            # ---- execute node ----
            t_node = time.perf_counter()
            error: str | None = None
            try:
                result_state = node.execute(state)
                # Normalise to AgentState
                if isinstance(result_state, dict) and not isinstance(
                    result_state, AgentState
                ):
                    state = AgentState(result_state)
                else:
                    state = result_state
            except Exception as exc:  # noqa: BLE001
                error = f"{type(exc).__name__}: {exc}"
            finally:
                t_end = time.perf_counter()
                output_keys = (
                    list(state.keys()) if error is None else input_keys
                )
                traces.append(
                    NodeTrace(
                        node_name=current,
                        node_type=node.node_type,
                        started_at=t_node,
                        ended_at=t_end,
                        duration_ms=(t_end - t_node) * 1000,
                        input_keys=input_keys,
                        output_keys=output_keys,
                        error=error,
                    )
                )

            if error is not None:
                break

            # ---- resolve next node ----
            current = self._resolve_next(current, state)

        total_ms = (time.perf_counter() - t0) * 1000
        success = all(t.error is None for t in traces)
        last_error = next(
            (t.error for t in reversed(traces) if t.error), None
        )

        result = AgentResult(
            output=state,
            trace=traces,
            total_ms=total_ms,
            nodes_executed=steps,
            graph_name=self.name,
            success=success,
            error=last_error,
        )

        if recorder is not None:
            self._record_telemetry(recorder, result)

        return result

    def _resolve_next(self, current: str, state: AgentState) -> str | None:
        """Follow the first outgoing edge whose condition is satisfied."""
        outgoing = [e for e in self._edges if e.source == current]
        if not outgoing:
            return None  # terminal node
        for edge in outgoing:
            if edge.evaluate(state):
                return edge.target
        return None  # no condition matched — dead end

    def _record_telemetry(
        self, recorder: Any, result: AgentResult
    ) -> None:
        """Record the graph execution as a telemetry event."""
        try:
            ev = recorder.new_event(
                "agent_run",
                namespace=self.name,
                latency_ms=result.total_ms,
                status="ok" if result.success else "error",
                error=result.error,
            )
            # Attach per-node trace as extra payload
            ev.extra = {
                "graph_name": self.name,
                "nodes_executed": result.nodes_executed,
                "trace": [t.to_dict() for t in result.trace],
            }
            recorder.record(ev)
        except Exception:  # noqa: BLE001 — telemetry must never crash
            pass

    # ------------------------------------------------------------- serialize

    def to_dict(self) -> dict:
        """Serialize the graph to a JSON-compatible dict.

        This is the format the ReactFlow canvas will consume.
        Callable conditions are emitted as descriptive strings (not
        round-trippable); use string conditions for full fidelity.
        """
        return {
            "name": self.name,
            "description": self.description,
            "entry": self._entry,
            "nodes": {
                name: {**node.to_dict(), "name": name}
                for name, node in self._nodes.items()
            },
            "edges": [e.to_dict() for e in self._edges],
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentGraph:
        """Reconstruct a graph from a dict produced by :meth:`to_dict`.

        Only nodes whose ``type`` is present in :data:`NODE_REGISTRY` and
        string conditions can be deserialized.  Callable conditions and
        nodes requiring live instances (e.g. ``RetrieverNode``) must be
        attached programmatically after deserialization.
        """
        graph = cls(data["name"], description=data.get("description", ""))

        for name, node_data in data.get("nodes", {}).items():
            node_type = node_data.get("type", "passthrough")
            node_cls = NODE_REGISTRY.get(node_type)
            if node_cls is None:
                raise ValueError(f"Unknown node type: {node_type!r}")
            node = node_cls.from_dict(node_data)
            graph.add_node(name, node)

        for edge_data in data.get("edges", []):
            condition = edge_data.get("condition")
            # Callable placeholders can't be re-hydrated
            if isinstance(condition, str) and condition.startswith("<callable:"):
                condition = None
            graph.add_edge(
                edge_data["source"],
                edge_data["target"],
                condition=condition,
                label=edge_data.get("label", ""),
            )

        if data.get("entry"):
            graph.set_entry(data["entry"])

        return graph

    def __repr__(self) -> str:
        return (
            f"AgentGraph({self.name!r}, nodes={len(self._nodes)}, "
            f"edges={len(self._edges)}, entry={self._entry!r})"
        )

