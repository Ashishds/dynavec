"""Built-in node types for the agent graph engine.

Every concrete node is registered in :data:`NODE_REGISTRY` via the
``@_register`` decorator so that :meth:`AgentGraph.from_dict` can
reconstruct graphs from JSON.
"""

from __future__ import annotations

from typing import Any, Callable

from .base import NODE_REGISTRY, AgentState, BaseNode

# ---------------------------------------------------------------------------
# Registration helper
# ---------------------------------------------------------------------------


def _register(cls: type[BaseNode]) -> type[BaseNode]:
    """Class decorator — adds *cls* to the global node registry."""
    NODE_REGISTRY[cls.node_type] = cls
    return cls


# ---------------------------------------------------------------------------
# Generic / structural nodes
# ---------------------------------------------------------------------------


@_register
class PassthroughNode(BaseNode):
    """Passes state through unchanged.  Useful for merge-points and tests."""

    node_type = "passthrough"

    def execute(self, state: AgentState) -> AgentState:
        return state


@_register
class FunctionNode(BaseNode):
    """Wraps an arbitrary Python callable as a graph node.

    The function receives an :class:`AgentState` and must return an
    :class:`AgentState` (or plain ``dict``).

    Example::

        FunctionNode(lambda s: s.set("upper", s["text"].upper()))
    """

    node_type = "function"

    def __init__(
        self,
        fn: Callable[[AgentState], AgentState | dict],
        *,
        label: str = "",
    ) -> None:
        self.fn = fn
        self.label = label or getattr(fn, "__name__", "fn")

    def execute(self, state: AgentState) -> AgentState:
        result = self.fn(state)
        if isinstance(result, dict) and not isinstance(result, AgentState):
            return AgentState(result)
        return result

    def to_dict(self) -> dict:
        return {"type": self.node_type, "label": self.label}

    @classmethod
    def from_dict(cls, data: dict) -> FunctionNode:
        # Callables can't be deserialized; return a passthrough placeholder
        return cls(fn=lambda s: s, label=data.get("label", "fn"))


@_register
class TransformNode(BaseNode):
    """Sets fixed default values on the state.

    Example::

        TransformNode(defaults={"model": "gpt-4o", "top_k": 10})
    """

    node_type = "transform"

    def __init__(self, *, defaults: dict[str, Any] | None = None) -> None:
        self.defaults = defaults or {}

    def execute(self, state: AgentState) -> AgentState:
        for k, v in self.defaults.items():
            state[k] = v
        return state

    def to_dict(self) -> dict:
        return {"type": self.node_type, "defaults": self.defaults}

    @classmethod
    def from_dict(cls, data: dict) -> TransformNode:
        return cls(defaults=data.get("defaults", {}))


@_register
class ResponseNode(BaseNode):
    """Terminal node that formats a final response string.

    * If ``message`` is set, it becomes ``state[output_field]`` verbatim.
    * If ``template`` is set, it's ``.format(**state)``-expanded.
    * Otherwise, state passes through unchanged.
    """

    node_type = "response"

    def __init__(
        self,
        *,
        message: str | None = None,
        template: str | None = None,
        output_field: str = "response",
    ) -> None:
        self.message = message
        self.template = template
        self.output_field = output_field

    def execute(self, state: AgentState) -> AgentState:
        if self.message is not None:
            state[self.output_field] = self.message
        elif self.template is not None:
            state[self.output_field] = self.template.format(**state)
        return state

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "type": self.node_type,
            "output_field": self.output_field,
        }
        if self.message is not None:
            d["message"] = self.message
        if self.template is not None:
            d["template"] = self.template
        return d

    @classmethod
    def from_dict(cls, data: dict) -> ResponseNode:
        return cls(
            message=data.get("message"),
            template=data.get("template"),
            output_field=data.get("output_field", "response"),
        )


# ---------------------------------------------------------------------------
# Data-processing nodes
# ---------------------------------------------------------------------------


@_register
class MapNode(BaseNode):
    """Applies a function to each item in a list field.

    Reads ``state[input_field]``, applies ``fn`` to each element,
    and writes the mapped list to ``state[output_field]``.
    """

    node_type = "map"

    def __init__(
        self,
        fn: Callable[[Any], Any],
        *,
        input_field: str = "items",
        output_field: str = "results",
    ) -> None:
        self.fn = fn
        self.input_field = input_field
        self.output_field = output_field

    def execute(self, state: AgentState) -> AgentState:
        items = state.get(self.input_field, [])
        state[self.output_field] = [self.fn(item) for item in items]
        return state

    def to_dict(self) -> dict:
        return {
            "type": self.node_type,
            "input_field": self.input_field,
            "output_field": self.output_field,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MapNode:
        return cls(
            fn=lambda x: x,
            input_field=data.get("input_field", "items"),
            output_field=data.get("output_field", "results"),
        )


@_register
class FilterNode(BaseNode):
    """Filters a list field, keeping items where ``predicate(item)`` is True."""

    node_type = "filter"

    def __init__(
        self,
        predicate: Callable[[Any], bool],
        *,
        input_field: str = "items",
        output_field: str = "filtered",
    ) -> None:
        self.predicate = predicate
        self.input_field = input_field
        self.output_field = output_field

    def execute(self, state: AgentState) -> AgentState:
        items = state.get(self.input_field, [])
        state[self.output_field] = [item for item in items if self.predicate(item)]
        return state

    def to_dict(self) -> dict:
        return {
            "type": self.node_type,
            "input_field": self.input_field,
            "output_field": self.output_field,
        }

    @classmethod
    def from_dict(cls, data: dict) -> FilterNode:
        return cls(
            predicate=lambda x: True,
            input_field=data.get("input_field", "items"),
            output_field=data.get("output_field", "filtered"),
        )


# ---------------------------------------------------------------------------
# RAG / AI-specific nodes
# ---------------------------------------------------------------------------


@_register
class GuardNode(BaseNode):
    """Checks a numeric score field against a threshold.

    Sets ``state["guard_passed"]`` (bool), ``state["guard_score"]``,
    and ``state["guard_threshold"]``.  Use edge conditions to branch::

        graph.add_edge("guard", "synth",    condition="guard_passed == True")
        graph.add_edge("guard", "fallback", condition="guard_passed == False")
    """

    node_type = "guard"

    def __init__(
        self,
        *,
        threshold: float = 0.35,
        score_field: str = "confidence",
    ) -> None:
        self.threshold = threshold
        self.score_field = score_field

    def execute(self, state: AgentState) -> AgentState:
        score = state.get(self.score_field, 0.0)
        if not isinstance(score, (int, float)):
            score = 0.0
        state["guard_passed"] = score >= self.threshold
        state["guard_score"] = score
        state["guard_threshold"] = self.threshold
        return state

    def to_dict(self) -> dict:
        return {
            "type": self.node_type,
            "threshold": self.threshold,
            "score_field": self.score_field,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GuardNode:
        return cls(
            threshold=data.get("threshold", 0.35),
            score_field=data.get("score_field", "confidence"),
        )


@_register
class RetrieverNode(BaseNode):
    """Performs a dynavec vector search.

    Requires a live :class:`~dynavec.Dynavec` client instance.  Sets
    ``state["results"]``, ``state["results_count"]``, and
    ``state["confidence"]`` (top score).
    """

    node_type = "retriever"

    def __init__(
        self,
        db: Any,
        *,
        top_k: int = 10,
        namespace: str = "default",
        query_field: str = "query",
        rerank: str | None = None,
    ) -> None:
        self.db = db
        self.top_k = top_k
        self.namespace = namespace
        self.query_field = query_field
        self.rerank = rerank

    def execute(self, state: AgentState) -> AgentState:
        query = state.get(self.query_field, "")
        kwargs: dict[str, Any] = {
            "top_k": self.top_k,
            "namespace": self.namespace,
        }
        if self.rerank:
            kwargs["rerank"] = self.rerank
        hits = self.db.search(query, **kwargs)
        state["results"] = hits
        state["results_count"] = len(hits)
        state["confidence"] = hits[0].score if hits else 0.0
        return state

    def to_dict(self) -> dict:
        return {
            "type": self.node_type,
            "top_k": self.top_k,
            "namespace": self.namespace,
            "query_field": self.query_field,
            "rerank": self.rerank,
        }

    @classmethod
    def from_dict(cls, data: dict) -> RetrieverNode:
        raise ValueError(
            "RetrieverNode requires a live 'db' instance and cannot be "
            "deserialized from JSON alone.  Construct it programmatically."
        )


@_register
class LLMNode(BaseNode):
    """Calls a large language model with a prompt template.

    The ``prompt_template`` is ``.format(**state)``-expanded, then
    passed to the provided ``call_fn``.  The LLM response is written
    to ``state[output_field]``.

    ``call_fn`` is any callable ``(str) -> str`` — wrap your OpenAI /
    Bedrock / Gemini client in one::

        def my_llm(prompt: str) -> str:
            return openai.chat.completions.create(
                model="gpt-4o", messages=[{"role": "user", "content": prompt}]
            ).choices[0].message.content

        LLMNode(call_fn=my_llm, prompt_template="Answer: {query}\\nContext: {context}")
    """

    node_type = "llm"

    def __init__(
        self,
        call_fn: Callable[[str], str],
        *,
        prompt_template: str = "{query}",
        output_field: str = "llm_response",
        label: str = "",
    ) -> None:
        self.call_fn = call_fn
        self.prompt_template = prompt_template
        self.output_field = output_field
        self.label = label

    def execute(self, state: AgentState) -> AgentState:
        prompt = self.prompt_template.format(**state)
        response = self.call_fn(prompt)
        state[self.output_field] = response
        return state

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "type": self.node_type,
            "prompt_template": self.prompt_template,
            "output_field": self.output_field,
        }
        if self.label:
            d["label"] = self.label
        return d

    @classmethod
    def from_dict(cls, data: dict) -> LLMNode:
        raise ValueError(
            "LLMNode requires a 'call_fn' callable and cannot be "
            "deserialized from JSON alone.  Construct it programmatically."
        )

