"""Shared, batched particle filter over (x, y, log10 A[Bq]) -- FR-EST-01..04.

The likelihood calls exactly the simulator's detector model
(:func:`radsearch.physics.expected_counts`) and attenuation kernel, so the
filter and the world can never disagree (FR-EST-02).

Three variants are implemented because TBq sources make the Poisson
likelihood extremely sharp (counts ~1e3-1e6, relative noise < 3 %), which
collapses a plain SIR filter (see docs/DESIGN_DECISIONS.md, D3):

* ``sir``      -- resample when ESS < ess_frac * P, no jitter.
* ``rpf``      -- regularised PF: Gaussian kernel jitter after resampling
                  (Silverman bandwidth, Musso et al. 2001).
* ``tempered`` -- rpf + adaptive likelihood tempering (progressive
                  correction, Oudjane & Musso 2000): the update is split into
                  stages whose exponents keep ESS >= ess_frac * P, with
                  resample + jitter between stages.
"""
from __future__ import annotations

import numpy as np

from . import physics as P
from ._kernels import loglik_bp


class ParticleFilter:
    def __init__(self, n_envs: int, n_particles: int, iso: P.Isotope, det: P.Detector,
                 dwell_s: float, logA_range=(12.0, 14.0), variant: str = "tempered",
                 ess_frac: float = 0.5, jitter_scale: float = 1.0, max_stages: int = 3,
                 min_sigma=(0.02, 0.02, 0.005), model_sigma: float = 0.0):
        assert variant in ("sir", "rpf", "tempered")
        self.B, self.P = n_envs, n_particles
        self.iso, self.det, self.dwell = iso, det, dwell_s
        self.logA_range = tuple(logA_range)
        self.variant = variant
        self.model_sigma = model_sigma
        self.ess_frac = ess_frac
        self.jitter_scale = jitter_scale
        self.max_stages = max_stages if variant == "tempered" else 1
        self.min_sigma = np.asarray(min_sigma)
        self.x = np.zeros((self.B, self.P, 3))
        self.logw = np.full((self.B, self.P), -np.log(self.P))
        self.rngs = [np.random.default_rng(i) for i in range(self.B)]
        self.rects = np.zeros((self.B, 0, 4))
        self.mu = np.zeros((self.B, 0))
        self.nrect = np.zeros(self.B, dtype=np.int64)
        self.occ = [None] * self.B
        self.room = np.zeros((self.B, 2))
        self.n_stages_used = np.zeros(self.B, dtype=np.int64)
        self._cache = None

    # ------------------------------------------------------------------ setup
    def set_geometry(self, rects, mu, nrect):
        self.rects, self.mu, self.nrect = rects, mu, nrect

    def reset(self, b: int, occ: np.ndarray, cell: float, rng: np.random.Generator):
        """Uniform prior over free floor space and log-uniform activity."""
        self.rngs[b] = rng
        self.occ[b] = occ
        self.cell = cell
        self.room[b] = np.array(occ.shape) * cell
        free = np.argwhere(~occ)
        idx = rng.integers(len(free), size=self.P)
        xy = (free[idx] + rng.random((self.P, 2))) * cell
        logA = rng.uniform(*self.logA_range, size=self.P)
        self.x[b] = np.column_stack([xy, logA])
        self.logw[b] = -np.log(self.P)
        self._cache = None

    # --------------------------------------------------------------- update
    def loglik(self, robot_xy, counts, active):
        """(B, P) log-likelihood of one synchronous measurement round."""
        return loglik_bp(self.x[..., :2], self.x[..., 2], robot_xy, counts, active,
                         self.rects, self.mu, self.nrect, self.iso, self.det, self.dwell,
                         self.model_sigma)

    def update(self, robot_xy, counts, active, envs=None):
        """Assimilate counts (B,N) taken at robot_xy (B,N,2); inactive robots ignored."""
        self._cache = None
        envs = np.arange(self.B) if envs is None else np.asarray(envs)
        active = active.astype(np.float64)
        has_meas = active.sum(-1) > 0
        remaining = np.where(has_meas, 1.0, 0.0)  # tempering budget left per env
        remaining[np.setdiff1d(np.arange(self.B), envs)] = 0.0
        self.n_stages_used[:] = 0
        for stage in range(self.max_stages):
            todo = remaining > 1e-9
            if not todo.any():
                break
            ll = self.loglik(robot_xy, counts, active)
            last = stage == self.max_stages - 1
            alpha = remaining.copy() if (self.variant != "tempered" or last) else \
                self._choose_alpha(ll, remaining)
            alpha[~todo] = 0.0
            self.logw = self.logw + alpha[:, None] * ll
            self._normalise()
            remaining = remaining - alpha
            self.n_stages_used += todo
            ess = self.ess()
            need = todo & (ess < self.ess_frac * self.P)
            if self.variant == "tempered":
                need = todo & ((ess < self.ess_frac * self.P) | (remaining > 1e-9))
            if need.any():
                self._resample(np.flatnonzero(need), jitter=self.variant != "sir")

    def _choose_alpha(self, ll, remaining):
        """Largest alpha <= remaining with ESS(w * L^alpha) >= ess_frac * P (bisection)."""
        target = self.ess_frac * self.P
        lo = np.zeros(self.B)
        hi = remaining.copy()
        ok_full = self._ess_after(ll, hi) >= target
        for _ in range(15):
            mid = 0.5 * (lo + hi)
            good = self._ess_after(ll, mid) >= target
            lo = np.where(good, mid, lo)
            hi = np.where(good, hi, mid)
        alpha = np.where(ok_full, remaining, lo)
        # always make progress, even if a single particle dominates
        return np.maximum(alpha, np.minimum(remaining, 1e-3))

    def _ess_after(self, ll, alpha):
        lw = self.logw + alpha[:, None] * ll
        lw = lw - lw.max(1, keepdims=True)
        w = np.exp(lw)
        return w.sum(1) ** 2 / (w * w).sum(1)

    def _normalise(self):
        m = self.logw.max(1, keepdims=True)
        self.logw = self.logw - (m + np.log(np.exp(self.logw - m).sum(1, keepdims=True)))

    def ess(self):
        w = np.exp(self.logw)
        return 1.0 / (w * w).sum(1)

    def _resample(self, envs, jitter: bool):
        w = np.exp(self.logw[envs])
        cdf = np.cumsum(w, axis=1)
        cdf[:, -1] = 1.0
        u0 = np.array([self.rngs[b].random() for b in envs])
        u = (u0[:, None] + np.arange(self.P)) / self.P
        idx = np.stack([np.searchsorted(cdf[i], u[i]) for i in range(len(envs))])
        idx = np.minimum(idx, self.P - 1)
        if jitter:
            mean, cov = self._moments(envs)
            d = 3
            h = self.jitter_scale * (4.0 / (d + 2)) ** (1 / (d + 4)) * self.P ** (-1 / (d + 4))
        for i, b in enumerate(envs):
            new = self.x[b, idx[i]]
            if jitter:
                sig = np.maximum(np.sqrt(np.clip(np.diag(cov[i]), 0, None)) * h, self.min_sigma)
                prop = new + self.rngs[b].normal(size=new.shape) * sig
                ok = self._valid(b, prop)
                new = np.where(ok[:, None], prop, new)
            self.x[b] = new
            self.logw[b] = -np.log(self.P)

    def _valid(self, b, xs):
        lo_a, hi_a = self.logA_range
        W, H = self.room[b]
        inb = (xs[:, 0] > 0) & (xs[:, 0] < W) & (xs[:, 1] > 0) & (xs[:, 1] < H)
        cx = np.clip((xs[:, 0] / self.cell).astype(int), 0, self.occ[b].shape[0] - 1)
        cy = np.clip((xs[:, 1] / self.cell).astype(int), 0, self.occ[b].shape[1] - 1)
        free = ~self.occ[b][cx, cy]
        # activity prior has hard support: keep the PF inside it
        ina = (xs[:, 2] >= lo_a - 0.5) & (xs[:, 2] <= hi_a + 0.5)
        return inb & free & ina

    # -------------------------------------------------------------- outputs
    def _moments(self, envs=None):
        envs = np.arange(self.B) if envs is None else envs
        w = np.exp(self.logw[envs])[..., None]
        x = self.x[envs]
        mean = (w * x).sum(1)
        dx = x - mean[:, None]
        cov = np.matmul((w * dx).transpose(0, 2, 1), dx)
        return mean, cov

    def estimate(self):
        """Posterior mean (B,3) and covariance (B,3,3) of (x, y, log10 A)  -- FR-EST-03.

        Cached until the particles change (update / reset)."""
        if self._cache is None:
            self._cache = self._moments()
        return self._cache

    def position_sigma(self):
        """sqrt of the largest eigenvalue of the (x, y) covariance, metres."""
        _, cov = self._moments()
        ev = np.linalg.eigvalsh(cov[:, :2, :2])
        return np.sqrt(np.clip(ev[:, -1], 0, None))

    def subsample(self, b: int, n: int, rng=None) -> np.ndarray:
        """n particles drawn by weight (for planners and the shield)."""
        rng = rng or self.rngs[b]
        w = np.exp(self.logw[b])
        idx = rng.choice(self.P, size=n, p=w / w.sum())
        return self.x[b, idx]
