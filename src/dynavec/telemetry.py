"""Telemetry capture for the observability dashboard.

This records **real** events from actual dynavec operations — every ``search``
is timed and logged with its namespace, latency, result count, cache outcome,
and score stats. There is no simulated traffic: if the dashboard shows numbers,
they came from real calls into the client.

Design
------
* :class:`TelemetryEvent` — one recorded operation (a "trace").
* :class:`TelemetryRecorder` — thread-safe ring buffer + aggregation. Attach it
  to a client (``Dynavec(..., telemetry=recorder)``) and it fills as you query.
* :func:`aggregate` — percentiles, QPM, cache-hit-rate, op mix, error rate,
  per-minute histogram — computed from the real events.

Zero third-party deps; safe to import with just the base install.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class TelemetryHook(Protocol):
    """Callback protocol for external observability integrations.

    Implement any subset of these methods and register with
    :meth:`TelemetryRecorder.add_hook`. Methods that are not implemented
    are simply not called (duck-typed via ``hasattr``).

    Example::

        class DataDogHook:
            def on_search_end(self, event: TelemetryEvent) -> None:
                statsd.histogram("dynavec.search.latency_ms", event.latency_ms)
                statsd.increment("dynavec.search.count")

        rec = TelemetryRecorder()
        rec.add_hook(DataDogHook())
    """

    def on_search_start(self, namespace: str, top_k: int) -> None: ...
    def on_search_end(self, event: TelemetryEvent) -> None: ...
    def on_cache_hit(self, namespace: str, top_k: int) -> None: ...
    def on_upsert(self, namespace: str, count: int) -> None: ...
    def on_error(self, op: str, error: str) -> None: ...


@dataclass
class TelemetryEvent:
    """A single recorded operation."""

    id: str
    ts: float  # epoch seconds (start)
    op: str  # "search" | "upsert" | "graph_search" | ...
    namespace: str = "default"
    latency_ms: float = 0.0
    n_results: int = 0
    top_k: int | None = None
    cache_hit: bool | None = None  # None = no cache configured
    filtered: bool = False
    rescore: str | None = None
    rerank: str | None = None
    score_top: float | None = None
    score_mean: float | None = None
    status: str = "ok"  # "ok" | "error"
    error: str | None = None
    query_preview: str | None = None  # only set when capture_text=True
    # per-phase timing breakdown (ms) — None if not instrumented
    embed_ms: float | None = None
    ann_ms: float | None = None
    hydrate_ms: float | None = None
    rerank_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TelemetryRecorder:
    """Thread-safe, bounded, in-process store of :class:`TelemetryEvent`.

    Parameters
    ----------
    max_events:
        Ring-buffer capacity (older events drop off).
    capture_text:
        If True, store a short preview of the query text. Off by default so no
        raw content is retained unless the operator opts in.
    """

    def __init__(self, max_events: int = 10_000, capture_text: bool = False) -> None:
        self._events: deque[TelemetryEvent] = deque(maxlen=max_events)
        self._lock = threading.Lock()
        self.capture_text = capture_text
        self._hooks: list[Any] = []

    # ------------------------------------------------------------------ hooks
    def add_hook(self, hook: Any) -> None:
        """Register an external observability hook.

        The hook should implement one or more of the :class:`TelemetryHook`
        methods.  Unimplemented methods are silently skipped.
        """
        self._hooks.append(hook)

    def remove_hook(self, hook: Any) -> None:
        """Unregister a previously added hook."""
        self._hooks = [h for h in self._hooks if h is not hook]

    def _fire(self, method: str, *args: Any, **kwargs: Any) -> None:
        """Call *method* on each hook that implements it, swallowing errors."""
        for hook in self._hooks:
            fn = getattr(hook, method, None)
            if fn is not None:
                try:
                    fn(*args, **kwargs)
                except Exception:  # noqa: BLE001
                    logger.debug("Hook %r.%s raised", hook, method, exc_info=True)

    # ------------------------------------------------------------------ record
    def record(self, event: TelemetryEvent) -> None:
        with self._lock:
            self._events.append(event)
        # Fire hooks outside the lock so slow hooks don't block recording.
        if event.status == "error":
            self._fire("on_error", event.op, event.error or "")
        elif event.op == "search":
            if event.cache_hit:
                self._fire("on_cache_hit", event.namespace, event.top_k or 0)
            self._fire("on_search_end", event)

    def new_event(self, op: str, **kw: Any) -> TelemetryEvent:
        return TelemetryEvent(id=uuid.uuid4().hex[:12], ts=time.time(), op=op, **kw)

    # ------------------------------------------------------------------- reads
    def events(
        self,
        limit: int = 200,
        op: str | None = None,
        namespace: str | None = None,
        status: str | None = None,
        since: float | None = None,
    ) -> list[TelemetryEvent]:
        with self._lock:
            items = list(self._events)
        out = []
        for e in reversed(items):  # newest first
            if op and e.op != op:
                continue
            if namespace and e.namespace != namespace:
                continue
            if status and e.status != status:
                continue
            if since and e.ts < since:
                continue
            out.append(e)
            if len(out) >= limit:
                break
        return out

    def get(self, event_id: str) -> TelemetryEvent | None:
        with self._lock:
            for e in self._events:
                if e.id == event_id:
                    return e
        return None

    def snapshot(self) -> list[TelemetryEvent]:
        with self._lock:
            return list(self._events)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * (pct / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = k - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def aggregate(
    events: list[TelemetryEvent],
    window_seconds: int = 3600,
    now: float | None = None,
    buckets: int = 30,
) -> dict[str, Any]:
    """Summarize events over the trailing ``window_seconds`` into dashboard stats."""
    now = now if now is not None else time.time()
    start = now - window_seconds
    win = [e for e in events if e.ts >= start]

    latencies = sorted(e.latency_ms for e in win if e.status == "ok")
    cache_scoped = [e for e in win if e.cache_hit is not None]
    hits = sum(1 for e in cache_scoped if e.cache_hit)
    errors = sum(1 for e in win if e.status == "error")

    op_mix: dict[str, int] = {}
    ns_mix: dict[str, int] = {}
    for e in win:
        op_mix[e.op] = op_mix.get(e.op, 0) + 1
        ns_mix[e.namespace] = ns_mix.get(e.namespace, 0) + 1

    # per-bucket count histogram across the window
    bucket_width = max(1.0, window_seconds / buckets)
    hist = [0] * buckets
    for e in win:
        idx = int((e.ts - start) / bucket_width)
        if 0 <= idx < buckets:
            hist[idx] += 1

    minutes = max(1e-9, window_seconds / 60.0)
    return {
        "total": len(win),
        "qpm": round(len(win) / minutes, 2),
        "p50": round(_percentile(latencies, 50), 2),
        "p95": round(_percentile(latencies, 95), 2),
        "p99": round(_percentile(latencies, 99), 2),
        "cache_hit_rate": round(100.0 * hits / len(cache_scoped), 1) if cache_scoped else None,
        "cache_hits": hits,
        "cache_total": len(cache_scoped),
        "error_rate": round(100.0 * errors / len(win), 2) if win else 0.0,
        "avg_results": round(sum(e.n_results for e in win) / len(win), 1) if win else 0.0,
        "op_mix": op_mix,
        "namespaces": ns_mix,
        "histogram": hist,
        "bucket_width_s": bucket_width,
        "window_start": start,
        "window_seconds": window_seconds,
    }
