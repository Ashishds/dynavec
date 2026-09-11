"""int8 Scalar Quantization for compact vector caching.

Where this helps: like :class:`~dynavec.quantization.ProductQuantizer`, scalar
quantization compresses vectors dynavec caches itself — the in-memory hot tier
and any local candidate cache.  Unlike PQ (which splits dimensions into
subspaces and k-means each), scalar quantization maps each dimension
independently to a uint8 range using learned per-dimension min/max bounds.

Trade-offs vs PQ:

* **Simpler & faster** — no k-means training, no per-subspace codebook lookup.
  ``fit()`` is O(n·d), not O(n·d·k·iters).
* **4× compression** — float32 (4 bytes) → uint8 (1 byte) per dimension.
  PQ can go further (8–32×) but at higher accuracy cost and training time.
* **Good default** — for hot-tier caching, the 4× scalar compression often
  delivers better accuracy-per-byte than PQ at the same code size, because it
  preserves the full dimensional structure.

Supports L2, cosine, and dot-product distance modes.
Pure numpy, no external deps.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ScalarQuantizer:
    """Per-dimension min/max quantization to uint8 (4× memory reduction).

    Parameters
    ----------
    clip_percentile:
        Percentile (0–50) at which to clip outlier values during calibration.
        ``1.0`` means the 1st and 99th percentile become the quantization
        bounds, which makes the quantizer robust to outliers.  ``0.0`` uses the
        raw min/max (sensitive to extreme values).
    """

    clip_percentile: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.clip_percentile < 50.0:
            raise ValueError(f"clip_percentile must be in [0, 50), got {self.clip_percentile}")
        self._mins: np.ndarray | None = None  # (d,)
        self._maxs: np.ndarray | None = None  # (d,)
        self._ranges: np.ndarray | None = None  # (d,) — precomputed max - min
        self._dimension: int | None = None

    # ------------------------------------------------------------------ train
    def fit(self, vectors: np.ndarray) -> ScalarQuantizer:
        """Calibrate quantization bounds from a representative sample.

        Parameters
        ----------
        vectors:
            (n, d) float array.  A few thousand vectors from the target
            distribution is plenty — the calibration is cheap.
        """
        x = np.asarray(vectors, dtype=np.float32)
        if x.ndim == 1:
            x = x.reshape(1, -1)
        if x.shape[0] == 0:
            raise ValueError("Cannot fit on an empty array")

        self._dimension = x.shape[1]

        if self.clip_percentile > 0.0:
            self._mins = np.percentile(x, self.clip_percentile, axis=0).astype(np.float32)
            self._maxs = np.percentile(x, 100.0 - self.clip_percentile, axis=0).astype(np.float32)
        else:
            self._mins = x.min(axis=0).astype(np.float32)
            self._maxs = x.max(axis=0).astype(np.float32)

        self._ranges = self._maxs - self._mins
        # Avoid division by zero for constant dimensions.
        self._ranges = np.where(self._ranges < 1e-12, 1.0, self._ranges)
        return self

    @property
    def is_fitted(self) -> bool:
        return self._mins is not None

    @property
    def dimension(self) -> int | None:
        """The dimensionality learned during ``fit()``, or None."""
        return self._dimension

    @property
    def code_size_bytes(self) -> int:
        """Bytes per encoded vector (1 byte per dimension)."""
        if self._dimension is None:
            return 0
        return self._dimension

    @property
    def compression_ratio(self) -> float:
        """Compression ratio vs float32 (always 4.0 for uint8 scalar quant)."""
        return 4.0

    # ----------------------------------------------------------------- encode
    def encode(self, vectors: np.ndarray) -> np.ndarray:
        """Quantize float32 vectors to uint8 codes.

        Parameters
        ----------
        vectors:
            (n, d) or (d,) float array.

        Returns
        -------
        (n, d) uint8 array.  Each value in [0, 255].
        """
        self._check_fitted()
        x = np.asarray(vectors, dtype=np.float32)
        if x.ndim == 1:
            x = x.reshape(1, -1)
        self._check_dimension(x)

        # Linear mapping: float → [0, 1] → [0, 255]
        normalized = (x - self._mins) / self._ranges
        # Clip to [0, 1] to handle values outside calibration bounds.
        normalized = np.clip(normalized, 0.0, 1.0)
        codes = np.round(normalized * 255.0).astype(np.uint8)
        return codes

    def decode(self, codes: np.ndarray) -> np.ndarray:
        """Approximate reconstruction from uint8 codes back to float32.

        Parameters
        ----------
        codes:
            (n, d) uint8 array from :meth:`encode`.

        Returns
        -------
        (n, d) float32 array — the dequantized approximation.
        """
        self._check_fitted()
        codes = np.atleast_2d(codes)
        normalized = codes.astype(np.float32) / 255.0
        return normalized * self._ranges + self._mins

    # --------------------------------------------------------------- distance
    def l2_distances(self, query: np.ndarray, codes: np.ndarray) -> np.ndarray:
        """Squared L2 distance from a full-precision query to encoded vectors.

        Dequantizes on the fly and computes exact L2 against the reconstructed
        vectors. For hot-tier ranking this is accurate enough; for the final
        result set the original float32 vectors from S3 Vectors are used.

        Parameters
        ----------
        query:
            (d,) float32 query vector.
        codes:
            (n, d) uint8 encoded vectors.

        Returns
        -------
        (n,) float32 array of squared L2 distances.
        """
        self._check_fitted()
        q = np.asarray(query, dtype=np.float32).reshape(-1)
        decoded = self.decode(codes)
        diff = decoded - q
        return (diff * diff).sum(axis=1)

    def cosine_similarities(self, query: np.ndarray, codes: np.ndarray) -> np.ndarray:
        """Cosine similarity from a full-precision query to encoded vectors.

        Parameters
        ----------
        query:
            (d,) float32 query vector.
        codes:
            (n, d) uint8 encoded vectors.

        Returns
        -------
        (n,) float32 array of cosine similarities in [-1, 1].
        """
        self._check_fitted()
        q = np.asarray(query, dtype=np.float32).reshape(-1)
        decoded = self.decode(codes)
        q_norm = np.linalg.norm(q) + 1e-12
        d_norms = np.linalg.norm(decoded, axis=1, keepdims=True) + 1e-12
        return ((decoded / d_norms) @ (q / q_norm)).ravel()

    def reconstruction_error(self, vectors: np.ndarray) -> float:
        """Mean squared reconstruction error (quality diagnostic).

        Returns the average per-vector MSE, so you can compare against
        :meth:`~dynavec.quantization.ProductQuantizer.reconstruction_error`.
        """
        x = np.asarray(vectors, dtype=np.float32)
        if x.ndim == 1:
            x = x.reshape(1, -1)
        recon = self.decode(self.encode(x))
        return float(((x - recon) ** 2).sum(axis=1).mean())

    # --------------------------------------------------------------- internals
    def _check_fitted(self) -> None:
        if self._mins is None:
            raise RuntimeError("ScalarQuantizer must be .fit() before use")

    def _check_dimension(self, x: np.ndarray) -> None:
        if x.shape[1] != self._dimension:
            raise ValueError(f"Input dimension {x.shape[1]} != fitted dimension {self._dimension}")
