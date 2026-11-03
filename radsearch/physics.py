"""Analytic radiation physics (FR-PHY-01 .. FR-PHY-08).

All functions are pure, NumPy-vectorised and broadcast over leading batch
dimensions, so the *same* code is used by the simulator (truth) and by the
particle filter (likelihood) -- FR-EST-02 is satisfied by construction.

Dose model and detector model are separate functions (FR-PHY-04); they share
only the geometry helper :func:`wall_optical_depth`.

Geometry conventions
--------------------
* Positions are 2-D floor-plane coordinates in metres, shape ``(..., 2)``.
* The source lies on the floor; the detector / robot electronics sit
  ``height`` metres above it, so the 3-D distance is
  ``sqrt(dx^2 + dy^2 + height^2)``. This is physical and removes the
  ``1/r^2`` singularity without an arbitrary clamp.
* Obstacles are axis-aligned rectangles ``[xmin, ymin, xmax, ymax]`` that are
  taller than the detector. The 3-D chord through a vertical-walled block is
  the 2-D chord times ``d3 / d2``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

CONSTANTS_FILE = Path(__file__).with_name("physics_constants.yaml")
SECONDS_PER_HOUR = 3600.0


@lru_cache(maxsize=None)
def load_constants(path: str | None = None) -> dict:
    with open(path or CONSTANTS_FILE) as f:
        return yaml.safe_load(f)


@dataclass(frozen=True)
class Isotope:
    name: str
    gamma_constant: float  # Gy m^2 / (GBq h)
    photons_per_decay: float
    mu_air: float  # 1/m
    mu_material: dict = field(default_factory=dict)  # 1/m

    @classmethod
    def from_constants(cls, name: str, constants: dict | None = None) -> "Isotope":
        c = (constants or load_constants())["isotopes"][name]
        return cls(
            name=name,
            gamma_constant=float(c["gamma_constant"]),
            photons_per_decay=float(c["photons_per_decay"]),
            mu_air=float(c["mu_air_per_m"]),
            mu_material={k: float(v) for k, v in c["mu_material_per_m"].items()},
        )


@dataclass(frozen=True)
class Detector:
    radius: float
    efficiency: float
    fit_m: float
    background_cps: float
    dead_time: float
    height: float

    @classmethod
    def from_constants(cls, constants: dict | None = None, **overrides) -> "Detector":
        c = (constants or load_constants())["detector"]
        kw = dict(
            radius=float(c["radius_m"]),
            efficiency=float(c["intrinsic_efficiency"]),
            fit_m=float(c["fit_m"]),
            background_cps=float(c["background_cps"]),
            dead_time=float(c["dead_time_s"]),
            height=float(c["height_m"]),
        )
        kw.update({k: float(v) for k, v in overrides.items() if v is not None})
        return cls(**kw)


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------
def rect_chord_lengths(p0: np.ndarray, p1: np.ndarray, rects: np.ndarray) -> np.ndarray:
    """2-D length of segment p0->p1 inside each rectangle (slab method).

    p0, p1: ``(..., 2)``; rects: ``(..., K, 4)`` broadcastable against
    ``p0[..., None, :]``. Returns ``(..., K)``. Exact for axis-aligned boxes.
    """
    p0 = np.asarray(p0)[..., None, :]
    p1 = np.asarray(p1)[..., None, :]
    d = p1 - p0
    lo = rects[..., :2]
    hi = rects[..., 2:]
    zero = d == 0.0
    safe_d = np.where(zero, 1.0, d)
    t1 = (lo - p0) / safe_d
    t2 = (hi - p0) / safe_d
    tmin = np.minimum(t1, t2)
    tmax = np.maximum(t1, t2)
    # Segment parallel to a slab: either always inside it or never.
    inside = (p0 >= lo) & (p0 <= hi)
    tmin = np.where(zero, np.where(inside, -np.inf, np.inf), tmin)
    tmax = np.where(zero, np.where(inside, np.inf, -np.inf), tmax)
    t_enter = np.maximum(tmin.max(-1), 0.0)
    t_exit = np.minimum(tmax.min(-1), 1.0)
    seg = np.sqrt((d * d).sum(-1))[..., 0]
    return np.clip(t_exit - t_enter, 0.0, None) * seg[..., None]


def distances(src: np.ndarray, det: np.ndarray, height: float):
    """Return (d2, d3): floor-plane and 3-D source-detector distances."""
    diff = np.asarray(det) - np.asarray(src)
    d2sq = (diff * diff).sum(-1)
    return np.sqrt(d2sq), np.sqrt(d2sq + height * height)


def wall_optical_depth(src, det, rects, mu_rects, height: float) -> np.ndarray:
    """Sum_i mu_i * l_i along the straight 3-D ray (FR-PHY-05).

    rects ``(..., K, 4)`` and mu_rects ``(..., K)`` -- padding rectangles must
    have ``mu = 0``. Returns an array with the broadcast shape of src/det.
    """
    if rects is None or rects.shape[-2] == 0:
        return np.zeros(np.broadcast_shapes(np.shape(src)[:-1], np.shape(det)[:-1]))
    chords = rect_chord_lengths(src, det, rects)
    tau2d = (chords * mu_rects).sum(-1)
    d2, d3 = distances(src, det, height)
    return tau2d * (d3 / np.maximum(d2, 1e-9))


# --------------------------------------------------------------------------
# Dose model (FR-PHY-01, FR-PHY-02)
# --------------------------------------------------------------------------
def dose_rate(src, activity_GBq, det, iso: Isotope, height: float, tau_wall=0.0,
              air_attenuation: bool = True) -> np.ndarray:
    """Dose rate in Gy/h:  Gamma * A / r^2 * exp(-tau_wall) [* exp(-mu_air r)]."""
    _, d3 = distances(src, det, height)
    rate = iso.gamma_constant * np.asarray(activity_GBq) / (d3 * d3) * np.exp(-tau_wall)
    if air_attenuation:
        rate = rate * np.exp(-iso.mu_air * d3)
    return rate


def step_dose(rate_Gy_per_h, dt_s: float) -> np.ndarray:
    return np.asarray(rate_Gy_per_h) * (dt_s / SECONDS_PER_HOUR)


# --------------------------------------------------------------------------
# Detector model (FR-PHY-03, FR-PHY-08)
# --------------------------------------------------------------------------
def geometric_efficiency(d3, det: Detector) -> np.ndarray:
    """0.5 * [1 - d / sqrt(r^2 + m d + d^2)] : fraction of photons hitting the face."""
    d3 = np.asarray(d3)
    return 0.5 * (1.0 - d3 / np.sqrt(det.radius ** 2 + det.fit_m * d3 + d3 * d3))


def expected_counts(src, activity_Bq, det_xy, iso: Isotope, det: Detector, dwell_s: float,
                    tau_wall=0.0) -> np.ndarray:
    """Mean counts in one dwell (Poisson parameter), incl. background and dead time."""
    _, d3 = distances(src, det_xy, det.height)
    rate = (np.asarray(activity_Bq) * iso.photons_per_decay * det.efficiency
            * geometric_efficiency(d3, det) * np.exp(-iso.mu_air * d3) * np.exp(-tau_wall))
    rate = rate + det.background_cps
    if det.dead_time > 0:  # non-paralysable dead time
        rate = rate / (1.0 + rate * det.dead_time)
    return rate * dwell_s


def sample_counts(rng: np.random.Generator, lam) -> np.ndarray:
    return rng.poisson(lam)


def poisson_loglik(k, lam) -> np.ndarray:
    """log p(k | lam) without the k-only constant -log(k!) (cancels in the PF)."""
    lam = np.maximum(lam, 1e-12)
    return k * np.log(lam) - lam


def apply_model_error(rng: np.random.Generator, lam, sigma: float, field=None):
    """Multiplicative model discrepancy (scatter/buildup, calibration).

    lam * exp(sigma * z - sigma^2 / 2), mean-preserving. ``field`` supplies a
    spatially correlated z (already standard normal); otherwise z is i.i.d.
    """
    if sigma <= 0:
        return lam
    z = rng.standard_normal(np.shape(lam)) if field is None else field
    return lam * np.exp(sigma * z - 0.5 * sigma * sigma)


def measurement_loglik(k, lam, sigma: float = 0.0):
    """Poisson log-lik if sigma == 0, else the log-normal-Poisson approximation
    log(k+0.5) ~ N(log(lam+0.5), sigma^2 + 1/(lam+0.5)) -- valid for both the
    low-count (Poisson) and high-count (model-error) regimes."""
    if sigma <= 0:
        return poisson_loglik(k, lam)
    lam = np.maximum(lam, 1e-12)
    v = sigma * sigma + 1.0 / (lam + 0.5)
    r = np.log(np.asarray(k) + 0.5) - np.log(lam + 0.5)
    return -0.5 * r * r / v - 0.5 * np.log(v)


GBQ = 1e9
TBQ = 1e12
