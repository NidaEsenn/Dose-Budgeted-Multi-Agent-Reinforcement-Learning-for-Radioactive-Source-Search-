from __future__ import annotations

import numpy as np

from ..shield import DoseShield, particle_predictions
from ..world import MOVES, N_ACTIONS, bfs_distances, ring_waypoints


class _Nav:
    """Cached BFS distance fields: one per (layout, target cell)."""

    def __init__(self):
        self._cache = {}

    def field(self, occ, target):
        key = (occ.tobytes(), tuple(int(v) for v in target))
        if key not in self._cache:
            if len(self._cache) > 4096:
                self._cache.clear()
            self._cache[key] = bfs_distances(occ, target)
        return self._cache[key]

    def step_towards(self, occ, cell, target):
        d = self.field(occ, target)
        W, H = occ.shape
        best, best_d = 4, d[cell[0], cell[1]]
        for a in range(4):
            nx, ny = cell[0] + MOVES[a][0], cell[1] + MOVES[a][1]
            if 0 <= nx < W and 0 <= ny < H and d[nx, ny] >= 0 and d[nx, ny] < best_d:
                best, best_d = a, d[nx, ny]
        return best


def nearest_free(occ, xy, cell=1.0):
    c = np.clip((np.asarray(xy) / cell).astype(int), 0, np.array(occ.shape) - 1)
    if not occ[c[0], c[1]]:
        return c
    free = np.argwhere(~occ)
    return free[np.argmin(np.abs(free - c).sum(1))]


class RandomPolicy:
    name = "random"

    def __init__(self, seed=0):
        self.rng = np.random.default_rng(seed)

    def reset(self, core, b):
        pass

    def act(self, core):
        return self.rng.integers(N_ACTIONS, size=(core.B, core.N))


class ApproachPolicy:
    """FR-BSL-02: every robot walks (BFS) to the cell of the current estimate."""
    name = "approach"

    def __init__(self):
        self.nav = _Nav()

    def reset(self, core, b):
        pass

    def act(self, core):
        mean, _ = core.pf.estimate()
        out = np.full((core.B, core.N), 4)
        for b in range(core.B):
            tgt = nearest_free(core.occ[b], mean[b, :2], core.cfg.cell)
            for i in range(core.N):
                if core.active[b, i]:
                    out[b, i] = self.nav.step_towards(core.occ[b], core.cells[b, i], tgt)
        return out


class PerimeterPolicy:
    """FR-BSL-03: robots split the wall-side ring into contiguous arcs and
    follow their arc clockwise once; afterwards they hold position while the
    estimator converges (multi-robot version of Son et al. 2025)."""
    name = "perimeter"

    def __init__(self, inset: int = 0):
        self.inset = inset
        self.nav = _Nav()
        self.plan, self.ptr = {}, {}

    def reset(self, core, b):
        ring = ring_waypoints(core.occ[b], self.inset)
        segs = np.array_split(np.arange(len(ring)), core.N)
        # assign arcs to robots greedily by distance to the arc start (door start)
        starts = [ring[s[0]] for s in segs]
        order, used = [], set()
        for i in range(core.N):
            d = [np.abs(core.cells[b, i] - st).sum() if k not in used else 1e9 for k, st in enumerate(starts)]
            k = int(np.argmin(d)); used.add(k); order.append(k)
        self.plan[b] = [ring[segs[k]] for k in order]
        self.ptr[b] = np.zeros(core.N, int)
        self._seed = core.ep_seed[b]

    def act(self, core):
        out = np.full((core.B, core.N), 4)
        for b in range(core.B):
            if b not in self.plan or core.t[b] == 0:
                self.reset(core, b)
            for i in range(core.N):
                if not core.active[b, i]:
                    continue
                path, p = self.plan[b][i], self.ptr[b][i]
                while p < len(path) and (core.cells[b, i] == path[p]).all():
                    p += 1
                self.ptr[b][i] = p
                if p < len(path):
                    out[b, i] = self.nav.step_towards(core.occ[b], core.cells[b, i], path[p])
        return out


class GreedyInfoPolicy:
    """FR-BSL-04: one-step greedy information seeker with a dose penalty.

    score(a) = I(a) - beta * E[step dose at a] / remaining budget,
    I = 0.5 * log(1 + Var[lambda] / E[lambda])  ("mi", Gaussian approximation
    of the mutual information of a Poisson count) or Var[log lambda]
    ("logvar"). With ``shield`` set this is the shielded greedy (FR-BSL-05).
    Robots choose sequentially; a robot's chosen cell is penalised for the
    following robots to avoid redundant measurements.
    """
    name = "greedy"

    def __init__(self, beta: float = 1.0, info: str = "mi", n_samples: int = 128,
                 shield: DoseShield | None = None, crowd_penalty: float = 0.5, seed: int = 0):
        self.beta, self.info, self.S = beta, info, n_samples
        self.shield = shield
        self.crowd = crowd_penalty
        self.rng = np.random.default_rng(seed)
        if shield is not None:
            self.name = "shielded_greedy"

    def reset(self, core, b):
        pass

    def act(self, core):
        dose, lam = particle_predictions(core, self.S, self.rng, counts=True)
        if self.info == "mi":
            I = 0.5 * np.log1p(lam.var(1) / np.maximum(lam.mean(1), 1e-9))
        else:
            I = np.log(lam).var(1)
        remaining = np.maximum(core.budget - core.dose, 1e-6)
        score = I - self.beta * dose.mean(1) / remaining[..., None]
        allowed = core.action_mask()
        if self.shield is not None:
            allowed &= self.shield.mask(core, dose)
        score = np.where(allowed, score, -np.inf)
        from ..shield import candidate_cells
        cand = candidate_cells(core)
        out = np.full((core.B, core.N), 4)
        for b in range(core.B):
            taken = []
            for i in range(core.N):
                s = score[b, i].copy()
                for c in taken:
                    same = (np.abs(cand[b, i] - c).sum(-1) == 0) & np.isfinite(s)
                    s = np.where(same, s - self.crowd * np.abs(s), s)
                a = int(np.argmax(s))
                out[b, i] = a
                taken.append(cand[b, i, a])
        return out


def make_baseline(name: str, **kw):
    name = name.lower()
    if name == "random":
        return RandomPolicy(**kw)
    if name == "approach":
        return ApproachPolicy()
    if name == "perimeter":
        return PerimeterPolicy(**kw)
    if name == "greedy":
        return GreedyInfoPolicy(**kw)
    if name == "shielded_greedy":
        shield_kw = {k: kw.pop(k) for k in list(kw) if k.startswith("shield_")}
        return GreedyInfoPolicy(shield=DoseShield(**{k[7:]: v for k, v in shield_kw.items()}), **kw)
    raise ValueError(name)
