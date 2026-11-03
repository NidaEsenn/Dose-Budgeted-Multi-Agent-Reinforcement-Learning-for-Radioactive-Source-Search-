"""Dose shield (FR-ALG-07, FR-BSL-05).

Uses only deployable information -- the shared particle filter, never the
true source. For every robot and candidate action it predicts the dose rate
at the resulting cell under ``S`` particles drawn from the posterior and
takes a high quantile (worst-case-ish). An action is blocked when

    dose_so_far + horizon * q_quantile(step dose at cell) >= margin * budget.

``horizon > 1`` reserves dose for the steps needed to back off again. If
every action is blocked the least-dangerous one is allowed, so the mask is
never empty.
"""
from __future__ import annotations

import numpy as np

from . import physics as P
from ._kernels import tau_bpn
from .world import MOVES, N_ACTIONS


def candidate_cells(core):
    cfg = core.cfg
    nxt = core.cells[:, :, None, :] + MOVES[None, None]            # (B,N,5,2)
    inb = (nxt[..., 0] >= 0) & (nxt[..., 0] < cfg.width) & (nxt[..., 1] >= 0) & (nxt[..., 1] < cfg.height)
    nxt = np.where(inb[..., None], nxt, core.cells[:, :, None, :])
    bi = np.arange(core.B)[:, None, None]
    blocked = core.occ[bi, nxt[..., 0], nxt[..., 1]]
    return np.where(blocked[..., None], core.cells[:, :, None, :], nxt)


def particle_predictions(core, n_samples: int = 128, rng=None, counts: bool = False):
    """Per-particle predicted step dose [Gy] (and expected counts) at every
    candidate cell, each (B, S, N, 5). Uses posterior samples only."""
    B, N = core.B, core.N
    rng = rng or np.random.default_rng(0)
    parts = np.stack([core.pf.subsample(b, n_samples, rng) for b in range(B)])  # (B,S,3)
    cand = (candidate_cells(core) + 0.5) * core.cfg.cell                         # (B,N,5,2)
    det = cand.reshape(B, N * N_ACTIONS, 2)
    tau = tau_bpn(parts[..., :2], det, core.rects, core.mu, core.nrect, core.det.height)  # (B,S,N*5)
    src, A = parts[:, :, None, :2], 10 ** parts[:, :, None, 2]
    rate = P.dose_rate(src, A / P.GBQ, det[:, None], core.iso, core.det.height, tau,
                       core.cfg.dose_air_attenuation)
    shape = (B, n_samples, N, N_ACTIONS)
    dose = P.step_dose(rate, core.cfg.step_time).reshape(shape)
    if not counts:
        return dose, None
    lam = P.expected_counts(src, A, det[:, None], core.iso, core.det, core.dwell, tau).reshape(shape)
    return dose, lam


class DoseShield:
    def __init__(self, quantile: float = 0.95, horizon: int = 3, margin: float = 1.0,
                 n_samples: int = 128, seed: int = 0):
        self.q, self.h, self.margin, self.S = quantile, horizon, margin, n_samples
        self.rng = np.random.default_rng(seed)

    def mask(self, core, pred=None) -> np.ndarray:
        """(B,N,5) bool allowed-action mask (always at least one True per robot)."""
        if pred is None:
            pred, _ = particle_predictions(core, self.S, self.rng)
        qd = np.quantile(pred, self.q, axis=1)                           # (B,N,5)
        limit = self.margin * core.budget[..., None]
        allowed = core.dose[..., None] + self.h * qd < limit
        none = ~allowed.any(-1)
        if none.any():
            best = np.argmin(qd, -1)
            allowed[none] = np.eye(N_ACTIONS, dtype=bool)[best[none]]
        allowed &= core.action_mask()
        allowed[~core.active] = np.eye(N_ACTIONS, dtype=bool)[4]
        return allowed
