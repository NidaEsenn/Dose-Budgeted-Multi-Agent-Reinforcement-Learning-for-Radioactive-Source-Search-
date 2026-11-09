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
        allowed[~core.active] = np.eye(N_ACTIONS, dtype=bool)[4]
        if core.n_actions > N_ACTIONS:           # withdraw is never blocked by the shield
            allowed = np.concatenate([allowed, core.active[..., None]], -1)
        return allowed & core.action_mask()


def predictive_fields(core, n_samples: int = 32, rng=None):
    """Step dose and exit dose [Gy] per cell under ``n_samples`` posterior particles,
    each (B,S,W,H). Deployable: uses the particle filter, never the true source."""
    from .env import exit_costs
    cfg = core.cfg
    B, S = core.B, n_samples
    rng = rng or np.random.default_rng(0)
    parts = np.stack([core.pf.subsample(b, S, rng) for b in range(B)])            # (B,S,3)
    cells = core._cell_xy                                                           # (M,2)
    M = cells.shape[0]
    det = np.broadcast_to(cells, (B * S, M, 2))
    src = parts.reshape(B * S, 1, 3)
    rep = lambda x: np.repeat(x, S, 0)
    tau = tau_bpn(src[..., :2], det, rep(core.rects), rep(core.mu), rep(core.nrect), core.det.height)[:, 0]
    rate = P.dose_rate(src[..., :2], 10 ** src[..., 2] / P.GBQ, det, core.iso, core.det.height, tau,
                       cfg.dose_air_attenuation)
    step = P.step_dose(rate, cfg.step_time).reshape(B * S, cfg.width, cfg.height)
    exitc = exit_costs(step, rep(core.door_dist))
    shp = (B, S, cfg.width, cfg.height)
    return step.reshape(shp), exitc.reshape(shp)


class ReserveWithdraw:
    """Wrap any policy with the per-step constraint C (K0.2):

        dose_so_far + step_dose(next cell) + exit_dose(next cell) <= margin * budget.

    If the base policy's chosen move would break it, the robot withdraws now
    (action 5) instead. ``mode="mean"`` predicts with the posterior mean,
    ``mode="quantile"`` with the q-quantile over posterior particles (robust to an
    overconfident filter). Needs ``EnvConfig.withdraw_action``.
    """

    def __init__(self, base, margin: float = 1.0, mode: str = "quantile", quantile: float = 0.9,
                 n_samples: int = 32, seed: int = 0):
        self.base, self.margin, self.mode, self.q, self.S = base, margin, mode, quantile, n_samples
        self.rng = np.random.default_rng(seed)
        self.name = f"{getattr(base, 'name', type(base).__name__)}+withdraw[{mode}]"

    def reset(self, core, b):
        if hasattr(self.base, "reset"):
            self.base.reset(core, b)

    def predicted(self, core):
        """(B,N,5) predicted step+exit dose for every candidate move."""
        if self.mode == "mean":
            step, exitc = core.estimated_fields()
            tot = (step + exitc)[:, None]                                    # (B,1,W,H)
        else:
            step, exitc = predictive_fields(core, self.S, self.rng)
            with np.errstate(invalid="ignore"):                               # inf on occupied cells
                tot = np.quantile(step + exitc, self.q, axis=1)[:, None]    # (B,1,W,H)
        cand = candidate_cells(core)                                          # (B,N,5,2)
        bi = np.arange(core.B)[:, None, None]
        return tot[bi, 0, cand[..., 0], cand[..., 1]]

    def act(self, core):
        act = np.asarray(self.base.act(core)).copy()
        if core.n_actions <= N_ACTIONS:
            return act
        pred = self.predicted(core)
        chosen = np.take_along_axis(pred, np.minimum(act, N_ACTIONS - 1)[..., None], -1)[..., 0]
        over = core.active & (core.dose + np.nan_to_num(chosen, nan=np.inf, posinf=np.inf)
                              > self.margin * core.budget)
        act[over] = 5
        return act


class ReserveShield:
    """Constraint C as an action mask (K0.2, Karar 3): a move is allowed only if

        dose_so_far + step_dose(next cell) + exit_dose(next cell) <= margin * budget,

    predicted with the q-quantile over posterior particles (or the posterior mean).
    Withdraw is always allowed, so the mask is never empty and a robot whose
    every move is unsafe can only leave. Masking keeps PPO on-policy.
    """

    def __init__(self, margin: float = 1.0, quantile: float = 0.97, mode: str = "quantile",
                 n_samples: int = 32, seed: int = 0):
        self._pred = ReserveWithdraw(None, margin, mode, quantile, n_samples, seed)
        self.margin = margin

    def mask(self, core, pred=None) -> np.ndarray:
        m = core.action_mask().copy()
        if core.n_actions <= N_ACTIONS:
            return m
        tot = self._pred.predicted(core)                                   # (B,N,5)
        safe = core.dose[..., None] + np.nan_to_num(tot, nan=np.inf) <= self.margin * core.budget[..., None]
        m[..., :N_ACTIONS] &= safe
        m[~core.active] = False
        m[~core.active, 4] = True
        return m
