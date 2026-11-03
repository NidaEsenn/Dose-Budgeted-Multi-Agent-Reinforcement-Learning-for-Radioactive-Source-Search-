"""Evaluate a checkpoint or baseline on the fixed test set and/or source grid.

    python -m radsearch.evaluate --policy runs/.../final.pt --env conf/env/main.yaml --episodes 1000
    python -m radsearch.evaluate --policy baseline:perimeter --grid --out results/perimeter_grid.json

The test set is seeds TEST_SEED_BASE + [0, n) (FR-EVAL-02). The grid mode
places the source at every free cell centre (every 1 m, FR-ENV-09) of fixed
reference layouts, with a fixed activity, for violation-rate maps.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
from omegaconf import OmegaConf

from .baselines import make_baseline
from .env import EnvConfig
from .eval.metrics import episode_metrics
from .eval.runner import TEST_SEED_BASE, run_episodes, test_seeds
from .world import generate_layout, source_grid

REFERENCE_LAYOUT_SEEDS = {"empty": (0, 0), "obstacles": (20_000_001, 5)}


def load_env_cfg(path_or_none, overrides=()) -> EnvConfig:
    from .train import to_env_cfg
    if path_or_none is None:
        base = OmegaConf.load("conf/env/main.yaml")
    else:
        base = OmegaConf.load(path_or_none)
        if "defaults" in base:
            parent = OmegaConf.load("conf/env/main.yaml")
            base.pop("defaults")
            base = OmegaConf.merge(parent, base)
    base = OmegaConf.merge(base, OmegaConf.from_dotlist(list(overrides)))
    return to_env_cfg(base)


def make_policy(spec: str, seed: int = 0):
    if spec.startswith("baseline:"):
        name, *kv = spec.split(":", 1)[1].split(",")
        kw = {k: float(v) for k, v in (x.split("=") for x in kv)}
        return make_baseline(name, **kw)
    from .algos.policy import load_policy
    return load_policy(spec, seed=seed)


def evaluate_policy(policy, cfg: EnvConfig, n_episodes=1000, seed_base=TEST_SEED_BASE, batch=16,
                    keep_episodes=True):
    eps, dt = run_episodes(policy, cfg, test_seeds(n_episodes, seed_base), batch=batch,
                           time_decisions=True)
    out = dict(metrics=episode_metrics(eps, cfg.cowardice_fraction), decision_time_s=dt)
    if keep_episodes:
        out["episodes"] = eps
    return out


def evaluate_grid(policy, cfg: EnvConfig, layout="obstacles", activity_TBq=10.0, batch=16):
    lay_seed, n_obs = REFERENCE_LAYOUT_SEEDS[layout]
    lay = generate_layout(np.random.default_rng(lay_seed), cfg.n_agents, cfg.width, cfg.height,
                          cfg.cell, n_obs, cfg.max_obstacle_size, cfg.materials, cfg.start_mode)
    pts = source_grid(lay)
    starts = lay.cell_center(lay.start_cells)
    keep = np.min(np.linalg.norm(pts[:, None] - starts[None], axis=-1), 1) >= 1.0
    pts = pts[keep]
    logA = np.log10(activity_TBq * 1e12)
    kwargs = [dict(layout=lay, source_xy=p, logA=logA) for p in pts]
    eps = run_episodes(policy, cfg, [30_000_000 + i for i in range(len(pts))], batch=batch,
                       reset_kwargs=kwargs)
    return dict(layout=layout, activity_TBq=activity_TBq, occ=lay.occ.astype(int).tolist(),
                rects=lay.rects.tolist(), sources=pts.tolist(),
                violation=[e["any_violation"] for e in eps], success=[e["success"] for e in eps],
                error=[e["error"] for e in eps], max_dose=[e["max_dose"] for e in eps],
                metrics=episode_metrics(eps, cfg.cowardice_fraction))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", required=True, help="checkpoint path or baseline:<name>[,k=v]")
    ap.add_argument("--env", default=None, help="env yaml (default conf/env/main.yaml)")
    ap.add_argument("--set", nargs="*", default=[], help="env overrides, e.g. n_agents=6")
    ap.add_argument("--episodes", type=int, default=1000)
    ap.add_argument("--grid", action="store_true")
    ap.add_argument("--grid_layout", default="obstacles")
    ap.add_argument("--out", default=None)
    ap.add_argument("--no_episodes", action="store_true", help="store metrics only")
    a = ap.parse_args()
    cfg = load_env_cfg(a.env, a.set)
    pol = make_policy(a.policy)
    res = dict(policy=a.policy, env=a.env, overrides=a.set)
    if a.episodes > 0:
        res["test"] = evaluate_policy(pol, cfg, a.episodes, keep_episodes=not a.no_episodes)
        print(json.dumps(res["test"]["metrics"], indent=1))
    if a.grid:
        res["grid"] = evaluate_grid(pol, cfg, a.grid_layout)
        print("grid:", json.dumps(res["grid"]["metrics"]))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(res, f)
