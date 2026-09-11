"""Tests for the telemetry recorder + aggregation (pure, no AWS)."""

import time

from dynavec.telemetry import TelemetryRecorder, aggregate


def _rec_with(events):
    r = TelemetryRecorder()
    for e in events:
        r.record(e)
    return r


def test_record_and_events_newest_first():
    r = TelemetryRecorder()
    for i in range(3):
        r.record(r.new_event("search", namespace="kb", latency_ms=float(i)))
    evs = r.events()
    assert len(evs) == 3
    assert evs[0].latency_ms == 2.0  # newest first


def test_events_filtering():
    r = TelemetryRecorder()
    r.record(r.new_event("search", namespace="a", status="ok"))
    r.record(r.new_event("upsert", namespace="b", status="ok"))
    r.record(r.new_event("search", namespace="a", status="error"))
    assert len(r.events(op="search")) == 2
    assert len(r.events(namespace="b")) == 1
    assert len(r.events(status="error")) == 1
    assert len(r.events(op="search", status="ok")) == 1


def test_get_and_limit():
    r = TelemetryRecorder()
    ev = r.new_event("search")
    r.record(ev)
    assert r.get(ev.id).id == ev.id
    assert r.get("nope") is None
    for _ in range(10):
        r.record(r.new_event("search"))
    assert len(r.events(limit=5)) == 5


def test_ring_buffer_caps_size():
    r = TelemetryRecorder(max_events=5)
    for _ in range(20):
        r.record(r.new_event("search"))
    assert len(r.snapshot()) == 5


def test_aggregate_percentiles_and_qpm():
    now = 1000.0
    evs = []
    r = TelemetryRecorder()
    for lat in range(1, 101):  # 100 events, latency 1..100ms
        evs.append(r.new_event("search", latency_ms=float(lat)))
    for e in evs:
        e.ts = now - 10  # all within window
    agg = aggregate(evs, window_seconds=3600, now=now)
    assert agg["total"] == 100
    assert 49 <= agg["p50"] <= 52
    assert 94 <= agg["p95"] <= 96
    assert agg["qpm"] == round(100 / 60.0, 2)


def test_aggregate_cache_hit_rate_and_errors():
    now = 500.0
    r = TelemetryRecorder()
    evs = [
        r.new_event("search", latency_ms=5, cache_hit=True),
        r.new_event("search", latency_ms=5, cache_hit=True),
        r.new_event("search", latency_ms=5, cache_hit=False),
        r.new_event("search", latency_ms=5, cache_hit=None),  # no cache configured
        r.new_event("search", latency_ms=5, status="error"),
    ]
    for e in evs:
        e.ts = now - 1
    agg = aggregate(evs, window_seconds=3600, now=now)
    assert agg["cache_total"] == 3  # None excluded
    assert agg["cache_hits"] == 2
    assert agg["cache_hit_rate"] == round(100 * 2 / 3, 1)
    assert agg["error_rate"] == round(100 * 1 / 5, 2)


def test_aggregate_window_excludes_old_events():
    now = 10_000.0
    r = TelemetryRecorder()
    old = r.new_event("search", latency_ms=5)
    old.ts = now - 5000
    new = r.new_event("search", latency_ms=5)
    new.ts = now - 10
    agg = aggregate([old, new], window_seconds=3600, now=now)
    assert agg["total"] == 1


def test_aggregate_histogram_buckets():
    now = 3600.0
    r = TelemetryRecorder()
    evs = []
    # one event in the first bucket, two in the last
    e0 = r.new_event("search", latency_ms=1)
    e0.ts = now - 3599
    e1 = r.new_event("search", latency_ms=1)
    e1.ts = now - 1
    e2 = r.new_event("search", latency_ms=1)
    e2.ts = now - 1
    evs = [e0, e1, e2]
    agg = aggregate(evs, window_seconds=3600, now=now, buckets=30)
    assert len(agg["histogram"]) == 30
    assert sum(agg["histogram"]) == 3
    assert agg["histogram"][0] == 1
    assert agg["histogram"][-1] == 2


def test_empty_aggregate_is_safe():
    agg = aggregate([], window_seconds=3600, now=time.time())
    assert agg["total"] == 0
    assert agg["p95"] == 0.0
    assert agg["cache_hit_rate"] is None


# ----------------------------------------------------------------- hooks


class _SpyHook:
    """Test hook that records all calls for assertion."""

    def __init__(self):
        self.search_starts = []
        self.search_ends = []
        self.cache_hits = []
        self.upserts = []
        self.errors = []

    def on_search_start(self, namespace, top_k):
        self.search_starts.append((namespace, top_k))

    def on_search_end(self, event):
        self.search_ends.append(event)

    def on_cache_hit(self, namespace, top_k):
        self.cache_hits.append((namespace, top_k))

    def on_upsert(self, namespace, count):
        self.upserts.append((namespace, count))

    def on_error(self, op, error):
        self.errors.append((op, error))


def test_hook_on_search_end_fires():
    r = TelemetryRecorder()
    spy = _SpyHook()
    r.add_hook(spy)
    ev = r.new_event("search", namespace="kb", latency_ms=5.0)
    r.record(ev)
    assert len(spy.search_ends) == 1
    assert spy.search_ends[0].namespace == "kb"


def test_hook_on_cache_hit_fires():
    r = TelemetryRecorder()
    spy = _SpyHook()
    r.add_hook(spy)
    ev = r.new_event("search", namespace="ns", cache_hit=True, top_k=10)
    r.record(ev)
    assert len(spy.cache_hits) == 1
    assert spy.cache_hits[0] == ("ns", 10)


def test_hook_on_error_fires():
    r = TelemetryRecorder()
    spy = _SpyHook()
    r.add_hook(spy)
    ev = r.new_event("search", status="error", error="boom")
    r.record(ev)
    assert len(spy.errors) == 1
    assert spy.errors[0] == ("search", "boom")


def test_hook_remove():
    r = TelemetryRecorder()
    spy = _SpyHook()
    r.add_hook(spy)
    r.remove_hook(spy)
    r.record(r.new_event("search"))
    assert len(spy.search_ends) == 0


def test_hook_error_does_not_crash_recorder():
    """A hook that raises should be silently swallowed."""

    class BrokenHook:
        def on_search_end(self, event):
            raise RuntimeError("hook crashed!")

    r = TelemetryRecorder()
    r.add_hook(BrokenHook())
    r.record(r.new_event("search"))  # should not raise
    assert len(r.events()) == 1


def test_partial_hook_only_implemented_methods():
    """A hook that only implements on_search_end should not crash."""

    class PartialHook:
        def __init__(self):
            self.called = False

        def on_search_end(self, event):
            self.called = True

    r = TelemetryRecorder()
    hook = PartialHook()
    r.add_hook(hook)
    r.record(r.new_event("search"))
    assert hook.called


def test_multiple_hooks():
    r = TelemetryRecorder()
    spy1 = _SpyHook()
    spy2 = _SpyHook()
    r.add_hook(spy1)
    r.add_hook(spy2)
    r.record(r.new_event("search"))
    assert len(spy1.search_ends) == 1
    assert len(spy2.search_ends) == 1


# ------------------------------------------------ timing breakdown fields


def test_timing_fields_in_event():
    r = TelemetryRecorder()
    ev = r.new_event(
        "search",
        embed_ms=1.5,
        ann_ms=20.0,
        hydrate_ms=3.0,
        rerank_ms=0.5,
    )
    assert ev.embed_ms == 1.5
    assert ev.ann_ms == 20.0
    assert ev.hydrate_ms == 3.0
    assert ev.rerank_ms == 0.5


def test_timing_fields_default_none():
    r = TelemetryRecorder()
    ev = r.new_event("search")
    assert ev.embed_ms is None
    assert ev.ann_ms is None
    assert ev.hydrate_ms is None
    assert ev.rerank_ms is None


def test_to_dict_includes_timing():
    r = TelemetryRecorder()
    ev = r.new_event("search", embed_ms=2.0, ann_ms=15.0)
    d = ev.to_dict()
    assert "embed_ms" in d
    assert d["embed_ms"] == 2.0
    assert d["ann_ms"] == 15.0
    assert d["hydrate_ms"] is None
