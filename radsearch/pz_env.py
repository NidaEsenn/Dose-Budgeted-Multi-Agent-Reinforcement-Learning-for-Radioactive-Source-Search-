"""PettingZoo ParallelEnv wrapper around a single-env core (FR-ENV-01).

Retired robots are *terminated* in PettingZoo terms and leave ``env.agents``;
their action mask (in ``infos[agent]["action_mask"]``) only allows "stay".
"""
from __future__ import annotations

import functools

import numpy as np
from gymnasium import spaces
from pettingzoo import ParallelEnv

from .env import EnvConfig, RadSearchCore
from .world import N_ACTIONS


class RadSearchParallelEnv(ParallelEnv):
    metadata = {"name": "radsearch_v0", "render_modes": ["rgb_array"], "is_parallelizable": True}

    def __init__(self, cfg: EnvConfig | None = None, render_mode=None, **overrides):
        cfg = cfg or EnvConfig()
        for k, v in overrides.items():
            setattr(cfg, k, v)
        self.cfg = cfg
        self.core = RadSearchCore(cfg, n_envs=1, autoreset=False)
        self.possible_agents = [f"robot_{i}" for i in range(cfg.n_agents)]
        self.agents = []
        self.render_mode = render_mode
        self._trajectory = []

    @functools.lru_cache(maxsize=None)
    def observation_space(self, agent):
        return spaces.Box(-np.inf, np.inf, shape=(self.core.obs_dim,), dtype=np.float32)

    @functools.lru_cache(maxsize=None)
    def action_space(self, agent):
        return spaces.Discrete(N_ACTIONS)

    def state(self):
        _, st = self.core.observe()
        return st[0, 0]

    def _infos(self):
        mask = self.core.action_mask()[0]
        return {a: {"action_mask": mask[i].astype(np.int8), "dose": float(self.core.dose[0, i]),
                    "budget": float(self.core.budget[0, i])}
                for i, a in enumerate(self.possible_agents) if a in self.agents}

    def reset(self, seed=None, options=None):
        allowed = ("layout", "source_xy", "logA", "budgets")
        options = {k: v for k, v in (options or {}).items() if k in allowed}
        self.core.reset_env(0, seed=seed, **options)
        self.agents = list(self.possible_agents)
        obs, _ = self.core.observe()
        self._trajectory = [self.core.robot_xy()[0].copy()]
        return {a: obs[0, i] for i, a in enumerate(self.agents)}, self._infos()

    def step(self, actions):
        act = np.full((1, self.cfg.n_agents), 4, dtype=np.int64)
        for i, a in enumerate(self.possible_agents):
            if a in actions and a in self.agents:
                act[0, i] = int(actions[a])
        out = self.core.step(act)
        self._trajectory.append(self.core.robot_xy()[0].copy())
        live = list(self.agents)
        done = bool(out["done"][0])
        trunc = bool(out["truncated"][0])
        rew = float(out["reward"][0])
        obs = out["obs"][0]
        observations = {a: obs[self.possible_agents.index(a)] for a in live}
        rewards = {a: rew for a in live}
        terminations, truncations = {}, {}
        for a in live:
            i = self.possible_agents.index(a)
            retired = not out["active"][0, i]
            terminations[a] = (done and not trunc) or retired
            truncations[a] = trunc and not retired
        infos = self._infos()
        for a in live:
            i = self.possible_agents.index(a)
            infos.setdefault(a, {})
            infos[a].update(cost_dose=float(out["cost_dose"][0, i]),
                            cost_violation=float(out["cost_violation"][0, i]))
            if done:
                infos[a]["episode"] = out["episodes"][0]
        self.agents = [a for a in live if not (terminations[a] or truncations[a])]
        return observations, rewards, terminations, truncations, infos

    def render(self):
        from .render import render_frame
        return render_frame(self.core, 0, np.array(self._trajectory))
