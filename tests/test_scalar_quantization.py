"""Tests for int8 Scalar Quantization (pure, no AWS).

Mirrors the structure of test_quantization.py for consistency, with additional
coverage for edge cases, accuracy bounds, and distance correctness.
"""

import numpy as np
import pytest

from dynavec.scalar_quantization import ScalarQuantizer

# ------------------------------------------------------------------ fixtures


@pytest.fixture
def clustered():
    """Synthetic clustered data — 500 vectors, 32 dims, 8 clusters."""
    rng = np.random.default_rng(42)
    centers = rng.normal(size=(8, 32)).astype(np.float32)
    assign = rng.integers(0, 8, size=500)
    x = centers[assign] + 0.05 * rng.normal(size=(500, 32)).astype(np.float32)
    return x.astype(np.float32)


@pytest.fixture
def uniform():
    """Uniform random data — 200 vectors, 64 dims."""
    rng = np.random.default_rng(123)
    return rng.uniform(-3.0, 3.0, size=(200, 64)).astype(np.float32)


@pytest.fixture
def high_dim():
    """High-dimensional data — 100 vectors, 1536 dims (OpenAI-sized)."""
    rng = np.random.default_rng(7)
    return rng.normal(size=(100, 1536)).astype(np.float32)


# ---------------------------------------------------------------- basic API


def test_fit_returns_self(clustered):
    sq = ScalarQuantizer()
    result = sq.fit(clustered)
    assert result is sq


def test_is_fitted_flag(clustered):
    sq = ScalarQuantizer()
    assert not sq.is_fitted
    sq.fit(clustered)
    assert sq.is_fitted


def test_dimension_property(clustered):
    sq = ScalarQuantizer().fit(clustered)
    assert sq.dimension == 32


def test_encode_shapes(clustered):
    sq = ScalarQuantizer().fit(clustered)
    codes = sq.encode(clustered)
    assert codes.shape == (500, 32)
    assert codes.dtype == np.uint8


def test_encode_single_vector(clustered):
    sq = ScalarQuantizer().fit(clustered)
    code = sq.encode(clustered[0])
    assert code.shape == (1, 32)
    assert code.dtype == np.uint8


def test_code_size_bytes(clustered):
    sq = ScalarQuantizer().fit(clustered)
    assert sq.code_size_bytes == 32  # 1 byte per dim


def test_compression_ratio():
    sq = ScalarQuantizer()
    assert sq.compression_ratio == 4.0


def test_decode_shapes(clustered):
    sq = ScalarQuantizer().fit(clustered)
    codes = sq.encode(clustered)
    decoded = sq.decode(codes)
    assert decoded.shape == clustered.shape
    assert decoded.dtype == np.float32


# ------------------------------------------------------ reconstruction quality


def test_reconstruction_error_is_small_for_clustered(clustered):
    sq = ScalarQuantizer(clip_percentile=0.0).fit(clustered)
    err = sq.reconstruction_error(clustered)
    # uint8 quantization of well-spread data: error should be small
    assert err < 0.5, f"Reconstruction error too high: {err}"


def test_reconstruction_error_decreases_with_no_clipping(uniform):
    sq_clip = ScalarQuantizer(clip_percentile=5.0).fit(uniform)
    sq_noclip = ScalarQuantizer(clip_percentile=0.0).fit(uniform)
    err_clip = sq_clip.reconstruction_error(uniform)
    err_noclip = sq_noclip.reconstruction_error(uniform)
    # No clipping should have lower error on the training data itself
    assert err_noclip <= err_clip + 1e-6


def test_roundtrip_within_quantization_step(clustered):
    """Decoded values should be within one quantization step of originals."""
    sq = ScalarQuantizer(clip_percentile=0.0).fit(clustered)
    decoded = sq.decode(sq.encode(clustered))
    # Max error per dimension should be bounded by step_size = range / 255
    ranges = clustered.max(axis=0) - clustered.min(axis=0)
    ranges = np.where(ranges < 1e-12, 1.0, ranges)
    step_sizes = ranges / 255.0
    max_errors = np.abs(clustered - decoded).max(axis=0)
    # Each dim's max error should be at most ~1 step (with small floating point margin)
    assert np.all(max_errors <= step_sizes * 1.1 + 1e-6)


def test_high_dimensional_reconstruction(high_dim):
    sq = ScalarQuantizer().fit(high_dim)
    err = sq.reconstruction_error(high_dim)
    # MSE scales with dimension (each dim contributes ~0.005 error for normal data).
    # 1536 × 0.005 ≈ 7.7; we allow 15.0 as a generous but still-meaningful bound.
    assert err < 15.0, f"High-dim reconstruction error too high: {err}"


# ----------------------------------------------------------- distance accuracy


def test_l2_distances_order_matches_exact(clustered):
    """L2 ranking from quantized vectors should largely agree with exact."""
    sq = ScalarQuantizer(clip_percentile=0.0).fit(clustered)
    codes = sq.encode(clustered)
    q = clustered[0]

    approx_dists = sq.l2_distances(q, codes)
    exact_dists = ((clustered - q) ** 2).sum(axis=1)

    # Top-10 nearest from approximate should overlap significantly with exact
    approx_top10 = set(np.argsort(approx_dists)[:10])
    exact_top10 = set(np.argsort(exact_dists)[:10])
    overlap = len(approx_top10 & exact_top10)
    assert overlap >= 6, f"Top-10 overlap only {overlap}/10"


def test_l2_distances_self_is_near_zero(clustered):
    sq = ScalarQuantizer(clip_percentile=0.0).fit(clustered)
    codes = sq.encode(clustered)
    q = clustered[0]
    dists = sq.l2_distances(q, codes)
    # Distance to self (quantized) should be very small
    assert dists[0] < 1.0


def test_cosine_similarities_self_is_near_one(clustered):
    sq = ScalarQuantizer(clip_percentile=0.0).fit(clustered)
    codes = sq.encode(clustered)
    q = clustered[0]
    sims = sq.cosine_similarities(q, codes)
    assert sims[0] > 0.95, f"Self-similarity too low: {sims[0]}"


def test_cosine_similarities_order_matches_exact(clustered):
    """Cosine ranking from quantized vectors should largely agree with exact."""
    sq = ScalarQuantizer(clip_percentile=0.0).fit(clustered)
    codes = sq.encode(clustered)
    q = clustered[0]

    approx_sims = sq.cosine_similarities(q, codes)
    # Exact cosine
    qn = q / (np.linalg.norm(q) + 1e-12)
    cn = clustered / (np.linalg.norm(clustered, axis=1, keepdims=True) + 1e-12)
    exact_sims = cn @ qn

    approx_top10 = set(np.argsort(-approx_sims)[:10])
    exact_top10 = set(np.argsort(-exact_sims)[:10])
    overlap = len(approx_top10 & exact_top10)
    assert overlap >= 6, f"Cosine top-10 overlap only {overlap}/10"


# ----------------------------------------------------------- edge cases


def test_constant_dimension_does_not_crash():
    """If a dimension is constant, quantization should still work."""
    x = np.ones((50, 8), dtype=np.float32)
    x[:, 0] = np.linspace(0, 1, 50)  # only dim 0 varies
    sq = ScalarQuantizer(clip_percentile=0.0).fit(x)
    codes = sq.encode(x)
    decoded = sq.decode(codes)
    # Constant dims should decode to the constant value
    assert np.allclose(decoded[:, 1], 1.0, atol=0.01)


def test_single_vector_fit():
    """Fitting on a single vector should not crash."""
    x = np.array([[1.0, 2.0, 3.0, 4.0]], dtype=np.float32)
    sq = ScalarQuantizer(clip_percentile=0.0).fit(x)
    codes = sq.encode(x)
    decoded = sq.decode(codes)
    # With a single point, min==max for each dim, so range is set to 1.0
    # and the encoded value should decode to the original (clamped)
    assert decoded.shape == (1, 4)


def test_empty_array_raises():
    x = np.zeros((0, 8), dtype=np.float32)
    with pytest.raises(ValueError, match="empty"):
        ScalarQuantizer().fit(x)


def test_dimension_mismatch_raises(clustered):
    sq = ScalarQuantizer().fit(clustered)  # 32 dims
    wrong = np.zeros((10, 64), dtype=np.float32)
    with pytest.raises(ValueError, match="dimension"):
        sq.encode(wrong)


def test_use_before_fit_raises():
    sq = ScalarQuantizer()
    with pytest.raises(RuntimeError, match="fit"):
        sq.encode(np.zeros((1, 16), dtype=np.float32))


def test_code_size_before_fit():
    sq = ScalarQuantizer()
    assert sq.code_size_bytes == 0
    assert sq.dimension is None


# ------------------------------------------------ clip_percentile validation


def test_negative_clip_percentile_raises():
    with pytest.raises(ValueError, match="clip_percentile"):
        ScalarQuantizer(clip_percentile=-1.0)


def test_clip_percentile_50_raises():
    with pytest.raises(ValueError, match="clip_percentile"):
        ScalarQuantizer(clip_percentile=50.0)


def test_clip_percentile_handles_outliers():
    """Clipping should make quantization robust to extreme outliers."""
    rng = np.random.default_rng(99)
    x = rng.normal(size=(500, 16)).astype(np.float32)
    # Add extreme outliers
    x[0, :] = 100.0
    x[1, :] = -100.0

    sq_noclip = ScalarQuantizer(clip_percentile=0.0).fit(x)
    sq_clipped = ScalarQuantizer(clip_percentile=2.0).fit(x)

    # Clipped version should have better reconstruction for the bulk data
    bulk = x[2:]  # exclude outliers
    err_noclip = sq_noclip.reconstruction_error(bulk)
    err_clipped = sq_clipped.reconstruction_error(bulk)
    assert err_clipped < err_noclip


# ----------------------------------------- comparison with ProductQuantizer


def test_scalar_vs_product_quantizer_accuracy(clustered):
    """ScalarQuantizer should have comparable accuracy to PQ at the same code size."""
    from dynavec.quantization import ProductQuantizer

    # Both produce 32-byte codes for 32-dim vectors
    sq = ScalarQuantizer(clip_percentile=0.0).fit(clustered)
    pq = ProductQuantizer(m=32, nbits=8).fit(clustered)  # m=32 → 32 bytes

    sq_err = sq.reconstruction_error(clustered)
    pq_err = pq.reconstruction_error(clustered)

    # SQ should be in the same ballpark (not orders of magnitude worse)
    assert sq_err < pq_err * 10, f"SQ error ({sq_err}) much worse than PQ error ({pq_err})"
