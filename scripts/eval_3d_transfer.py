"""Sim-to-sim transfer: run a grid-trained policy with MuJoCo robot motion at
several robot speeds and compare with the grid simulator on the same missions.

    python scripts/eval_3d_transfer.py --policy models/mappo_sanity_0.1Gy.pt --episodes 30
"""
import argparse
import json

import numpy as np

from radsearch.eval.metrics import episode_metrics
from radsearch.eval.runner import run_episodes, test_seeds
from radsearch.evaluate import load_env_cfg, make_policy
from radsearch.sim3d.runner import run_mission_3d

ap = argparse.ArgumentParser()
ap.add_argument("--policy", required=True)
ap.add_argument("--episodes", type=int, default=30)
ap.add_argument("--speeds", default="0.5,0.15,0.08")
ap.add_argument("--set", nargs="*", default=["budget_base_Gy=0.1"])
ap.add_argument("--out", default=None)
a = ap.parse_args()
cfg = load_env_cfg(None, a.set)
seeds = test_seeds(a.episodes)
rows = []
m = episode_metrics(run_episodes(make_policy(a.policy), cfg, seeds))
rows.append(dict(setting="grid (2-D)", success=m["success_rate"], violation=m["violation_rate"],
                 steps=m["steps_mean"], track_err_mean=0.0))
for v in map(float, a.speeds.split(",")):
    pol = make_policy(a.policy)
    eps, errs = [], []
    for s in seeds:
        r = run_mission_3d(pol, cfg, s, v_max=v)
        eps.append(r["episode"]); errs += [l["track_error"] for l in r["log"]]
    m = episode_metrics(eps)
    rows.append(dict(setting=f"MuJoCo 3-D, {v} m/s", success=m["success_rate"], violation=m["violation_rate"],
                     steps=m["steps_mean"], track_err_mean=float(np.mean(errs))))
for r in rows:
    print(json.dumps({k: round(x, 3) if isinstance(x, float) else x for k, x in r.items()}))
if a.out:
    json.dump(rows, open(a.out, "w"), indent=1)
