"""Batched dose-budgeted multi-robot source-search simulator.

``RadSearchCore`` steps ``n_envs`` independent rooms at once (FR-ENV-07). The
PettingZoo ``ParallelEnv`` in :mod:`radsearch.pz_env` wraps a core with
``n_envs = 1`` (FR-ENV-01).

Per step (FR-ENV-05): every active robot moves one cell (or stays), receives
``dose_rate x step_time`` at its new cell (FR-PHY-02), and takes one Poisson
measurement (FR-PHY-03). The shared particle filter assimilates all
measurements (FR-EST-01). A robot whose cumulative dose reaches its budget is
retired (FR-BUD-03): it no longer moves, measures or accrues dose, and its
later steps are flagged inactive so trainers can drop them (FR-BUD-04).

Every env slot owns its own ``np.random.Generator``, re-created from the
episode seed at reset, so an episode is bit-identical whatever the batch
composition (FR-ENV-06, NFR-01).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

import numpy as np

from . import physics as P
from ._kernels import tau_bpn
from .estimator import ParticleFilter
from .world import MOVES, N_ACTIONS, Layout, bfs_distances, generate_layout, sample_source

COUNT_NORM = np.log1p(1e7)


@dataclass
class EnvConfig:
    # world (FR-ENV-02/03/09/10)
    width: int = 20
    height: int = 20
    cell: float = 1.0
    n_agents: int = 4
    max_agents: int = 6                 # padding for teammate features (E5 generalisation)
    n_obstacles: tuple = (0, 7)
    max_obstacle_size: int = 4
    materials: tuple = ("concrete",)
    start_mode: str = "door"
    min_source_dist: float = 5.0
    # physics (FR-PHY-06)
    isotope: str = "Co-60"            # calibrated main setting (D7)
    activity_TBq: tuple = (10.0, 100.0)  # log-uniform; strong sources, where budgets bind (D21)
    dose_air_attenuation: bool = True
    detector: dict = field(default_factory=dict)   # overrides of physics_constants.yaml
    # multiplicative model error (docs/DESIGN_DECISIONS.md D6): "none" | "iid" | "field"
    model_error: str = "field"
    model_error_sigma: float = 0.3
    model_error_length: float = 3.0            # correlation length of the "field" mode [m]
    pf_model_sigma: float | None = None        # PF assumption; default = model_error_sigma
    # time (FR-ENV-05)
    step_time: float = 10.0
    dwell_fraction: float = 1.0
    max_steps: int = 200
    # budgets (FR-BUD-01/02)
    budget_base_Gy: float = 0.1         # AC-3 with egress + strong sources (D21)
    budget_base_range: tuple | None = None   # log-uniform per episode if set
    budget_ratio: tuple = (1.0,)              # cycled over robots, normalised to mean 1
    shuffle_budgets: bool = False             # fixed robot<->budget map: per-robot lambda (D9)
    retire: bool = True
    budget_ref_Gy: float = 2.0                # observation normaliser
    # estimator
    n_particles: int = 2000
    pf_variant: str = "tempered"
    pf_max_stages: int = 3
    pf_logA_range: tuple | None = None        # default: training activity range
    # reward (FR-OBS-03..05)
    err_scale: float = 5.0
    time_penalty: float = 0.005
    success_bonus: float = 1.0
    success_radius: float = 1.0
    dose_penalty_beta: float = 0.0            # fixed-penalty baseline (FR-ALG-05)
    terminate_on_confident: bool = True
    confident_sigma: float = 0.3
    min_steps: int = 5
    # observation switches (ablations, E4)
    obs_budget: bool = True
    obs_dose_rate: bool = True
    # D21: a robot must be able to drive back to the door when the mission ends;
    # its exit dose is added, and a robot that would exceed its budget is stranded.
    egress_required: bool = True
    # D21: predicted step dose for each move + estimated exit dose, from the team estimate
    obs_predicted_dose: bool = True
    cowardice_fraction: float = 0.1


def _free_run_lengths(occ: np.ndarray) -> np.ndarray:
    """(W,H,4) free cells before hitting a wall/obstacle in each action direction."""
    W, H = occ.shape
    out = np.zeros((W, H, 4))
    # up (+y): scan from the top row down; run[y] = 0 if y+1 blocked/out else run[y+1]+1
    run = np.zeros(W)
    for y in range(H - 1, -1, -1):
        out[:, y, 0] = run
        run = np.where(occ[:, y], 0, run + 1)
    run = np.zeros(W)
    for y in range(H):
        out[:, y, 1] = run
        run = np.where(occ[:, y], 0, run + 1)
    run = np.zeros(H)
    for x in range(W):
        out[x, :, 2] = run
        run = np.where(occ[x, :], 0, run + 1)
    run = np.zeros(H)
    for x in range(W - 1, -1, -1):
        out[x, :, 3] = run
        run = np.where(occ[x, :], 0, run + 1)
    return out


def exit_costs(step_dose: np.ndarray, door_dist: np.ndarray) -> np.ndarray:
    """Dose [Gy] to drive from every cell to the door, (B,W,H).

    Follows a shortest route (grid BFS distance to the door) and, among equally
    short routes, the one with the least dose. A robot accrues the step dose of
    every cell it enters; the door cell itself costs 0. Unreachable/occupied
    cells get +inf. Vectorised over the batch, one pass per BFS level.
    """
    cost = np.where(door_dist == 0, 0.0, np.inf)
    maxd = int(door_dist.max()) if door_dist.size else 0
    for k in range(1, maxd + 1):
        v = np.pad(step_dose + cost, ((0, 0), (1, 1), (1, 1)), constant_values=np.inf)
        m = np.minimum(np.minimum(v[:, 2:, 1:-1], v[:, :-2, 1:-1]), np.minimum(v[:, 1:-1, 2:], v[:, 1:-1, :-2]))
        cost = np.where(door_dist == k, m, cost)
    return cost


class RadSearchCore:
    def __init__(self, cfg: EnvConfig, n_envs: int = 1, seed: int = 0, autoreset: bool = True):
        self.cfg = cfg
        self.B, self.N = n_envs, cfg.n_agents
        assert self.N <= cfg.max_agents
        self.autoreset = autoreset
        self.iso = P.Isotope.from_constants(cfg.isotope)
        self.det = P.Detector.from_constants(**cfg.detector)
        self.dwell = cfg.step_time * cfg.dwell_fraction
        self.logA_range = (np.log10(cfg.activity_TBq[0] * P.TBQ), np.log10(cfg.activity_TBq[1] * P.TBQ))
        self.pf = ParticleFilter(self.B, cfg.n_particles, self.iso, self.det, self.dwell,
                                 logA_range=cfg.pf_logA_range or self.logA_range,
                                 variant=cfg.pf_variant, max_stages=cfg.pf_max_stages,
                                 model_sigma=self._pf_sigma())
        self._slot_rng = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(self.B)]
        self.K = cfg.n_obstacles if np.isscalar(cfg.n_obstacles) else cfg.n_obstacles[1]
        self.K = max(int(self.K), 1)
        B, N, K = self.B, self.N, self.K
        self.rects = np.zeros((B, K, 4)); self.mu = np.zeros((B, K)); self.nrect = np.zeros(B, np.int64)
        self.occ = np.zeros((B, cfg.width, cfg.height), bool)
        self.runlen = np.zeros((B, cfg.width, cfg.height, 4))
        self.layouts: list[Layout | None] = [None] * B
        self.src = np.zeros((B, 2)); self.logA = np.zeros(B)
        self.cells = np.zeros((B, N, 2), np.int64)
        self.budget = np.ones((B, N)); self.dose = np.zeros((B, N))
        self.active = np.ones((B, N), bool); self.violated = np.zeros((B, N), bool)
        self.violation_step = -np.ones((B, N), np.int64)
        self.t = np.zeros(B, np.int64); self.err = np.zeros(B)
        self.last_counts = np.zeros((B, N)); self.last_rate = np.zeros((B, N))
        self.max_rate_map = np.ones(B); self.max_rate_visited = np.zeros((B, N))
        self.first_hit = -np.ones(B, np.int64); self.ep_return = np.zeros(B)
        self.ep_seed = np.zeros(B, np.int64)
        self.min_dist = np.zeros(B)
        self.door_dist = -np.ones((B, cfg.width, cfg.height), np.int64)
        self.exit_true = np.zeros((B, cfg.width, cfg.height))
        self.exit_dose = np.zeros((B, N)); self.stranded = np.zeros((B, N), bool)
        gx, gy = np.meshgrid(np.arange(cfg.width), np.arange(cfg.height), indexing="ij")
        self._cell_xy = (np.stack([gx.ravel(), gy.ravel()], -1) + 0.5) * cfg.cell   # (W*H, 2)
        self.obs_dim = len(self._agent_obs_names())
        self.state_dim = self._state_dim()

    def _pf_sigma(self):
        cfg = self.cfg
        if cfg.pf_model_sigma is not None:
            return cfg.pf_model_sigma
        return 0.0 if cfg.model_error == "none" else cfg.model_error_sigma

    def _sample_field(self, rng):
        """Standard-normal Gaussian random field on the cell grid (FFT filter)."""
        cfg = self.cfg
        W, H = cfg.width, cfg.height
        n = rng.standard_normal((2 * W, 2 * H))
        kx = np.fft.fftfreq(2 * W, d=cfg.cell)[:, None]
        ky = np.fft.fftfreq(2 * H, d=cfg.cell)[None, :]
        filt = np.exp(-2 * (np.pi * cfg.model_error_length) ** 2 * (kx ** 2 + ky ** 2))
        f = np.real(np.fft.ifft2(np.fft.fft2(n) * np.sqrt(filt)))[:W, :H]
        return (f - f.mean()) / (f.std() + 1e-12)

    # ---------------------------------------------------------------- reset
    def reset_env(self, b: int, seed: int | None = None, layout: Layout | None = None,
                  source_xy=None, logA=None, budgets=None):
        cfg = self.cfg
        if seed is None:
            seed = int(self._slot_rng[b].integers(2 ** 62))
        self.ep_seed[b] = seed
        rng = np.random.default_rng(seed)
        r_layout, r_src, r_bud, r_pf, r_meas = [np.random.default_rng(s) for s in
                                                np.random.SeedSequence(seed).spawn(5)]
        lay = layout or generate_layout(r_layout, self.N, cfg.width, cfg.height, cfg.cell,
                                        cfg.n_obstacles, cfg.max_obstacle_size, cfg.materials,
                                        cfg.start_mode)
        self.layouts[b] = lay
        k = len(lay.rects)
        self.rects[b] = 0.0; self.mu[b] = 0.0; self.nrect[b] = k
        self.rects[b, :k] = lay.rects
        self.mu[b, :k] = [self.iso.mu_material[m] for m in lay.materials]
        self.occ[b] = lay.occ
        self.runlen[b] = _free_run_lengths(lay.occ)
        self.src[b] = sample_source(r_src, lay, cfg.min_source_dist) if source_xy is None else source_xy
        self.logA[b] = r_src.uniform(*self.logA_range) if logA is None else logA
        self.budget[b] = self._sample_budgets(r_bud) if budgets is None else budgets
        self.cells[b] = lay.start_cells
        self.cont_xy = None
        self.dose[b] = 0.0; self.active[b] = True; self.violated[b] = False
        self.violation_step[b] = -1; self.t[b] = 0; self.first_hit[b] = -1; self.ep_return[b] = 0.0
        self.last_counts[b] = 0.0
        self.max_rate_visited[b] = 0.0
        self.pf.set_geometry(self.rects, self.mu, self.nrect)
        self.pf.reset(b, lay.occ, cfg.cell, r_pf)
        self._meas_rng = getattr(self, "_meas_rng", [None] * self.B)
        self._meas_rng[b] = r_meas
        self._field = getattr(self, "_field", np.zeros((self.B, cfg.width, cfg.height)))
        if cfg.model_error == "field":
            self._field[b] = self._sample_field(np.random.default_rng(r_meas.integers(2 ** 62)))
        # true dose-rate field over free cells: cowardice metric + renderer
        free_xy = lay.cell_center(lay.free_cells)
        rates = self.true_dose_rate(b, free_xy)
        self.max_rate_map[b] = rates.max()
        self.door_dist[b] = bfs_distances(lay.occ, lay.door)
        all_rates = self.true_dose_rate(b, self._cell_xy).reshape(cfg.width, cfg.height)
        self.exit_true[b] = exit_costs(P.step_dose(all_rates, cfg.step_time)[None], self.door_dist[b:b + 1])[0]
        self.exit_dose[b] = 0.0; self.stranded[b] = False
        self.last_rate[b] = self.true_dose_rate(b, self.robot_xy()[b])
        self.max_rate_visited[b] = self.last_rate[b]
        self.min_dist[b] = np.linalg.norm(self.robot_xy()[b] - self.src[b], axis=1).min()
        mean, _ = self.pf.estimate()
        self.err[b] = np.linalg.norm(mean[b, :2] - self.src[b])
        return rng

    def _sample_budgets(self, rng):
        cfg = self.cfg
        base = cfg.budget_base_Gy
        if cfg.budget_base_range is not None:
            lo, hi = cfg.budget_base_range
            base = float(np.exp(rng.uniform(np.log(lo), np.log(hi))))
        ratio = np.resize(np.asarray(cfg.budget_ratio, float), self.N)
        ratio = ratio / ratio.mean()
        if cfg.shuffle_budgets:
            ratio = rng.permutation(ratio)
        return base * ratio

    def reset_all(self, seeds=None):
        for b in range(self.B):
            self.reset_env(b, None if seeds is None else seeds[b])
        return self.observe()

    # --------------------------------------------------------------- physics
    def robot_xy(self):
        if getattr(self, "cont_xy", None) is not None:
            return self.cont_xy
        return (self.cells + 0.5) * self.cfg.cell

    def true_dose_rate(self, b: int, xy: np.ndarray) -> np.ndarray:
        """Gy/h at points ``xy`` (M,2) in env ``b``."""
        tau = tau_bpn(self.src[b][None, None], xy[None], self.rects[b:b + 1], self.mu[b:b + 1],
                      self.nrect[b:b + 1], self.det.height)[0, 0]
        return P.dose_rate(self.src[b], 10 ** self.logA[b] / P.GBQ, xy, self.iso, self.det.height,
                           tau, self.cfg.dose_air_attenuation)

    # ------------------------------------------------------------------ step
    def step(self, actions: np.ndarray, xy_override: np.ndarray | None = None):
        """actions (B,N) int. Returns a dict of arrays; finished episodes in ``episodes``.

        ``xy_override`` (B,N,2): continuous robot positions reached by an external
        motion simulator (e.g. the MuJoCo 3-D world). Dose, counts and the
        estimator then use these real positions; the grid cell is updated to the
        cell the robot actually stands in.
        """
        cfg = self.cfg
        B, N = self.B, self.N
        acting = self.active.copy()
        # 1. motion (moves into walls/obstacles leave the robot in place)
        mv = MOVES[np.asarray(actions)] * acting[..., None]
        nxt = self.cells + mv
        inb = (nxt[..., 0] >= 0) & (nxt[..., 0] < cfg.width) & (nxt[..., 1] >= 0) & (nxt[..., 1] < cfg.height)
        nxt = np.where(inb[..., None], nxt, self.cells)
        bi = np.arange(B)[:, None]
        blocked = self.occ[bi, nxt[..., 0], nxt[..., 1]]
        self.cells = np.where(blocked[..., None], self.cells, nxt)
        if xy_override is not None:
            xy_override = np.asarray(xy_override, dtype=np.float64)
            c = np.floor(xy_override / cfg.cell).astype(np.int64)
            c[..., 0] = np.clip(c[..., 0], 0, cfg.width - 1)
            c[..., 1] = np.clip(c[..., 1], 0, cfg.height - 1)
            free = ~self.occ[bi, c[..., 0], c[..., 1]]
            self.cells = np.where(free[..., None], c, self.cells)
            self.cont_xy = xy_override.copy()
        xy = self.robot_xy()
        # 2. dose (truth)
        tau = tau_bpn(self.src[:, None], xy, self.rects, self.mu, self.nrect, self.det.height)[:, 0]
        rate = P.dose_rate(self.src[:, None], 10 ** self.logA[:, None] / P.GBQ, xy, self.iso,
                           self.det.height, tau, cfg.dose_air_attenuation)
        d_step = P.step_dose(rate, cfg.step_time) * acting
        self.dose += d_step
        self.last_rate = np.where(acting, rate, self.last_rate)
        self.max_rate_visited = np.maximum(self.max_rate_visited, np.where(acting, rate, 0))
        dsrc = np.linalg.norm(xy - self.src[:, None], axis=-1)
        self.min_dist = np.minimum(self.min_dist, np.where(acting, dsrc, np.inf).min(1))
        newly = acting & ~self.violated & (self.dose >= self.budget)
        self.violated |= newly
        self.violation_step = np.where(newly, self.t[:, None], self.violation_step)
        if cfg.retire:
            self.active &= ~newly
        # 3. measurement by robots that acted this step
        lam = P.expected_counts(self.src[:, None], 10 ** self.logA[:, None], xy, self.iso, self.det,
                                self.dwell, tau)
        if cfg.model_error == "iid":
            lam = np.stack([P.apply_model_error(self._meas_rng[b], lam[b], cfg.model_error_sigma)
                            for b in range(B)])
        elif cfg.model_error == "field":
            z = self._field[np.arange(B)[:, None], self.cells[..., 0], self.cells[..., 1]]
            lam = P.apply_model_error(None, lam, cfg.model_error_sigma, field=z)
        counts = np.stack([self._meas_rng[b].poisson(lam[b]) for b in range(B)]).astype(float)
        self.last_counts = np.where(acting, counts, self.last_counts)
        self.pf.update(xy, counts, acting)
        # 4. reward
        mean, cov = self.pf.estimate()
        err = np.linalg.norm(mean[:, :2] - self.src, axis=1)
        self.t += 1
        reward = (self.err - err) / cfg.err_scale - cfg.time_penalty
        if cfg.dose_penalty_beta > 0:
            reward -= cfg.dose_penalty_beta * (d_step / self.budget).sum(1)
        self.err = err
        hit = (err < cfg.success_radius) & (self.first_hit < 0)
        self.first_hit = np.where(hit, self.t, self.first_hit)
        sigma = np.sqrt(np.clip(np.linalg.eigvalsh(cov[:, :2, :2])[:, -1], 0, None))
        confident = cfg.terminate_on_confident & (sigma < cfg.confident_sigma) & (self.t >= cfg.min_steps)
        all_retired = ~self.active.any(1)
        truncated = self.t >= cfg.max_steps
        done = confident | all_retired | truncated
        success = done & (err < cfg.success_radius)
        reward = reward + cfg.success_bonus * success
        self.ep_return += reward
        # 5. costs (FR-ALG-03/04), normalised by each robot's budget
        cost_dose = d_step / self.budget
        cost_violation = newly.astype(float)
        # 6. egress (D21): robots still in the field must drive back to the door
        if cfg.egress_required and done.any():
            ix = np.flatnonzero(done)
            ex = self.exit_true[ix[:, None], self.cells[ix, :, 0], self.cells[ix, :, 1]] * self.active[ix]
            ex = np.where(np.isfinite(ex), ex, 0.0)
            self.exit_dose[ix] = ex
            self.dose[ix] += ex
            strand = self.active[ix] & ~self.violated[ix] & (self.dose[ix] >= self.budget[ix])
            self.stranded[ix] = strand
            self.violated[ix] |= strand
            self.violation_step[ix] = np.where(strand, self.t[ix, None], self.violation_step[ix])
            cost_dose[ix] += ex / self.budget[ix]
            cost_violation[ix] += strand

        episodes = []
        out_obs_final = None
        if done.any():
            for b in np.flatnonzero(done):
                episodes.append(self.episode_info(b, bool(confident[b]), bool(truncated[b])))
        out = dict(reward=reward, cost_dose=cost_dose, cost_violation=cost_violation,
                   acting=acting, done=done, truncated=truncated & ~confident & ~all_retired,
                   episodes=episodes, counts=counts, dose_step=d_step)
        if self.autoreset and done.any():
            for b in np.flatnonzero(done):
                self.reset_env(b)
        out["obs"], out["state"] = self.observe()
        out["active"] = self.active.copy()
        return out

    def episode_info(self, b, confident=False, truncated=False) -> dict:
        mean, cov = self.pf.estimate()
        lay = self.layouts[b]
        return dict(
            seed=int(self.ep_seed[b]), steps=int(self.t[b]), n_agents=self.N,
            n_obstacles=int(self.nrect[b]), source=self.src[b].tolist(),
            activity_TBq=float(10 ** self.logA[b] / P.TBQ),
            estimate=mean[b].tolist(), error=float(self.err[b]),
            success=bool(self.err[b] < self.cfg.success_radius),
            time_to_localize=int(self.first_hit[b]) if self.first_hit[b] > 0 else int(self.cfg.max_steps),
            budget=self.budget[b].tolist(), dose=self.dose[b].tolist(),
            violated=self.violated[b].tolist(), violation_step=self.violation_step[b].tolist(),
            any_violation=bool(self.violated[b].any()), max_dose=float(self.dose[b].max()),
            team_dose=float(self.dose[b].sum()),
            max_rate_frac=float(self.max_rate_visited[b].max() / max(self.max_rate_map[b], 1e-30)),
            min_source_dist=float(self.min_dist[b]), ret=float(self.ep_return[b]), confident=confident, truncated=truncated,
            exit_dose=self.exit_dose[b].tolist(), stranded=self.stranded[b].tolist(),
            any_stranded=bool(self.stranded[b].any()),
            door=list(lay.door),
        )

    # ----------------------------------------------------------- observation
    def _agent_obs_names(self):
        names = ["x", "y", "log_count", "log_dose_rate", "budget", "remaining", "time_left"]
        names += [f"blocked_{d}" for d in "udlr"] + [f"free_{d}" for d in "udlr"]
        names += ["est_dx", "est_dy", "est_x", "est_y", "est_sx", "est_sy", "est_logA", "est_slogA"]
        for j in range(self.cfg.max_agents - 1):
            names += [f"tm{j}_{k}" for k in ("present", "dx", "dy", "active", "budget", "remaining")]
        if self.cfg.obs_predicted_dose:
            names += [f"pred_dose_{d}" for d in ("u", "d", "l", "r", "stay")] + ["exit_reserve"]
        return names

    def estimated_fields(self):
        """Step dose [Gy] and exit dose [Gy] per cell, (B,W,H) each, from the
        team's *estimate* (posterior mean) -- deployable, never the truth."""
        cfg = self.cfg
        mean, _ = self.pf.estimate()
        M = self._cell_xy.shape[0]
        cells = np.broadcast_to(self._cell_xy, (self.B, M, 2))
        tau = tau_bpn(mean[:, None, :2], cells, self.rects, self.mu, self.nrect, self.det.height)[:, 0]
        rate = P.dose_rate(mean[:, None, :2], 10 ** mean[:, None, 2] / P.GBQ, cells, self.iso,
                           self.det.height, tau, cfg.dose_air_attenuation)
        step = P.step_dose(rate, cfg.step_time).reshape(self.B, cfg.width, cfg.height)
        return step, exit_costs(step, self.door_dist)

    def _state_dim(self):
        return 6 * self.cfg.max_agents + 3 + 6 + 1

    def observe(self, with_pred: bool | None = None):
        """Per-agent observations (B,N,obs_dim) and centralised state (B,N,state_dim).

        The state (critic input, FR-OBS-02) holds every robot's status, the
        true source position/activity, the estimate and the time; trainers
        concatenate it with the agent's own observation (agent-specific state).
        """
        cfg = self.cfg
        B, N, M = self.B, self.N, cfg.max_agents
        W, H = cfg.width * cfg.cell, cfg.height * cfg.cell
        xy = self.robot_xy()
        mean, cov = self.pf.estimate()
        std = np.sqrt(np.clip(np.diagonal(cov, axis1=1, axis2=2), 0, None))
        remaining = np.clip(1.0 - self.dose / self.budget, 0, 1)
        bud = self.budget / cfg.budget_ref_Gy
        if not cfg.obs_budget:
            remaining = np.zeros_like(remaining); bud = np.zeros_like(bud)
        lrate = (np.log10(np.maximum(self.last_rate, 1e-6)) + 2.0) / 4.0
        if not cfg.obs_dose_rate:
            lrate = np.zeros_like(lrate)
        bi = np.arange(B)[:, None]
        run = self.runlen[bi, self.cells[..., 0], self.cells[..., 1]]  # (B,N,4)
        tl = 1.0 - self.t / cfg.max_steps
        lA0 = self.logA_range[0]; lAw = self.logA_range[1] - self.logA_range[0]
        own = [xy[..., 0] / W, xy[..., 1] / H, np.log1p(self.last_counts) / COUNT_NORM, lrate,
               bud, remaining, np.repeat(tl[:, None], N, 1)]
        own = np.stack(own, -1)
        prox = np.concatenate([(run == 0).astype(float), run / max(cfg.width, cfg.height)], -1)
        est = np.stack([(mean[:, None, 0] - xy[..., 0]) / W, (mean[:, None, 1] - xy[..., 1]) / H,
                        np.repeat(mean[:, None, 0] / W, N, 1), np.repeat(mean[:, None, 1] / H, N, 1),
                        np.repeat(std[:, None, 0] / W, N, 1), np.repeat(std[:, None, 1] / H, N, 1),
                        np.repeat(((mean[:, 2] - lA0) / lAw)[:, None], N, 1),
                        np.repeat((std[:, 2] / lAw)[:, None], N, 1)], -1)
        # teammates sorted by distance (permutation invariant, padded to max_agents-1)
        rel = xy[:, None, :, :] - xy[:, :, None, :]           # (B, i, j, 2)
        dist = np.linalg.norm(rel, axis=-1) + np.eye(N)[None] * 1e9
        order = np.argsort(dist, axis=-1)[..., :N - 1]          # (B,N,N-1)
        tm = np.zeros((B, N, M - 1, 6))
        if N > 1:
            g = lambda a: np.take_along_axis(a[:, None, :].repeat(N, 1), order, -1)
            rx = np.take_along_axis(rel[..., 0], order, -1) / W
            ry = np.take_along_axis(rel[..., 1], order, -1) / H
            tm[:, :, :N - 1] = np.stack([np.ones_like(rx), rx, ry, g(self.active.astype(float)),
                                         g(bud), g(remaining)], -1)
        parts = [own, prox, est, tm.reshape(B, N, -1)]
        if cfg.obs_predicted_dose if with_pred is None else with_pred:
            from .shield import candidate_cells
            step, exitc = self.estimated_fields()
            rem = np.maximum(self.budget - self.dose, 1e-9)
            cand = candidate_cells(self)                                       # (B,N,5,2)
            pred = step[np.arange(B)[:, None, None], cand[..., 0], cand[..., 1]] / rem[..., None]
            ex = exitc[np.arange(B)[:, None], self.cells[..., 0], self.cells[..., 1]] / rem
            feat = np.concatenate([pred, ex[..., None]], -1)
            feat = np.clip(np.nan_to_num(feat, nan=3.0, posinf=3.0), 0, 3) / 3.0
            if not cfg.obs_budget:
                feat = np.zeros_like(feat)
            parts.append(feat)
        obs = np.concatenate(parts, -1).astype(np.float32)
        # centralised state
        st = np.zeros((B, M, 6))
        st[:, :N] = np.stack([xy[..., 0] / W, xy[..., 1] / H, self.active.astype(float),
                              self.budget / cfg.budget_ref_Gy, np.clip(1 - self.dose / self.budget, 0, 1),
                              lrate], -1)
        glob = np.concatenate([st.reshape(B, -1), self.src / np.array([W, H]),
                               ((self.logA - lA0) / lAw)[:, None],
                               mean[:, :2] / np.array([W, H]), ((mean[:, 2] - lA0) / lAw)[:, None],
                               std[:, :2] / np.array([W, H]), (std[:, 2] / lAw)[:, None],
                               tl[:, None]], -1)
        state = np.repeat(glob[:, None], N, 1).astype(np.float32)
        return obs, state

    def action_mask(self):
        """(B,N,5): retired robots may only 'stay'. Moves into walls are legal no-ops."""
        m = np.ones((self.B, self.N, N_ACTIONS), bool)
        m[~self.active] = False
        m[~self.active, 4] = True
        return m

    def config_dict(self):
        return asdict(self.cfg)
