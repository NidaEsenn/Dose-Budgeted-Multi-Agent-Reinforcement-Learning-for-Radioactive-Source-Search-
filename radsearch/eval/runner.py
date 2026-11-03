"""Run any policy (baseline or learned) on a fixed list of episode seeds.

Episode ``i`` of the test set always uses seed ``test_seed_base + i`` and is
evaluated with autoreset disabled, so every method sees exactly the same rooms,
sources and activities (FR-EVAL-02).
"""
from __future__ import annotations

import time

import numpy as np

from ..env import EnvConfig, RadSearchCore

TEST_SEED_BASE = 10_000_000


def test_seeds(n: int = 1000, base: int = TEST_SEED_BASE):
    return [base + i for i in range(n)]


def run_episodes(policy, cfg: EnvConfig, seeds, batch: int = 16, reset_kwargs=None,
                 record_trajectories: bool = False, time_decisions: bool = False):
    """Returns a list of episode-info dicts (order = seeds order)."""
    results = [None] * len(seeds)
    decision_times = []
    for start in range(0, len(seeds), batch):
        chunk = list(range(start, min(start + batch, len(seeds))))
        core = RadSearchCore(cfg, len(chunk), autoreset=False)
        for j, i in enumerate(chunk):
            kw = (reset_kwargs[i] if reset_kwargs is not None else {})
            core.reset_env(j, seed=seeds[i], **kw)
            if hasattr(policy, "reset"):
                policy.reset(core, j)
        live = np.ones(len(chunk), bool)
        trajs = [[core.robot_xy()[j].copy()] for j in range(len(chunk))]
        while live.any():
            t0 = time.perf_counter()
            act = policy.act(core)
            decision_times.append((time.perf_counter() - t0) / max(live.sum(), 1))
            act = np.where(live[:, None], act, 4)
            out = core.step(act)
            for j in range(len(chunk)):
                if live[j]:
                    trajs[j].append(core.robot_xy()[j].copy())
            for ep in out["episodes"]:
                j = [k for k in range(len(chunk)) if seeds[chunk[k]] == ep["seed"]][0]
                if live[j]:
                    if record_trajectories:
                        ep["trajectory"] = np.array(trajs[j]).tolist()
                    results[chunk[j]] = ep
                    live[j] = False
            # finished envs keep stepping with "stay"; freeze them so they cannot re-finish
            core.t[~live] = 0
            core.active[~live] = False
    if time_decisions:
        return results, float(np.median(decision_times))
    return results
