"""Aggregate evaluation results over training seeds (FR-EVAL-03).

* Violation / success rates: pooled over all seeds' test episodes with a
  Wilson 95 % interval, plus per-seed IQM with a stratified-bootstrap CI.
* Continuous metrics (error, dose, time): IQM over seeds with rliable CIs.

    python scripts/aggregate.py --exp E1 --tag test --out docs/results/E1.md
"""
import argparse
import glob
import json
import os
from collections import defaultdict

import numpy as np

from radsearch.eval.metrics import aggregate_over_seeds, wilson_interval

KEYS = ["success_rate", "violation_rate", "error_median", "max_dose_frac_mean", "team_dose_mean",
        "time_to_localize_mean", "cowardice_rate", "risk_sharing_mean"]

ap = argparse.ArgumentParser()
ap.add_argument("--exp", required=True)
ap.add_argument("--tag", default="test")
ap.add_argument("--root", default="runs")
ap.add_argument("--out", default=None)
a = ap.parse_args()

groups = defaultdict(list)
for path in glob.glob(os.path.join(a.root, a.exp, "*", "*", "seed*", f"eval_{a.tag}.json")):
    algo, env = path.split(os.sep)[-4], path.split(os.sep)[-3]
    groups[(algo, env)].append(json.load(open(path)))

rows = []
for (algo, env), runs in sorted(groups.items()):
    per_seed = {k: np.array([r["test"]["metrics"][k] for r in runs], float) for k in KEYS}
    eps = [e for r in runs for e in r["test"]["episodes"]]
    kv = sum(e["any_violation"] for e in eps); ks = sum(e["success"] for e in eps)
    row = dict(algo=algo, env=env, seeds=len(runs), episodes=len(eps),
               violation_pooled=kv / len(eps), violation_wilson=wilson_interval(kv, len(eps)),
               success_pooled=ks / len(eps), success_wilson=wilson_interval(ks, len(eps)))
    for k in KEYS:
        v = per_seed[k][np.isfinite(per_seed[k])]
        if len(v) >= 2:
            row[k] = aggregate_over_seeds(v[:, None])
        elif len(v) == 1:
            row[k] = dict(iqm=float(v[0]), iqm_ci=[float("nan")] * 2)
    rows.append(row)

lines = [f"# {a.exp} ({a.tag})", "",
         "| algo | env | seeds | violation (pooled, Wilson 95%) | success (pooled) | error IQM [CI] | max dose/budget IQM | cowardice | risk sharing |",
         "|---|---|---|---|---|---|---|---|---|"]
f = lambda d: f"{d['iqm']:.3f} [{d['iqm_ci'][0]:.3f}, {d['iqm_ci'][1]:.3f}]" if d else "-"
for r in rows:
    lines.append(f"| {r['algo']} | {r['env']} | {r['seeds']} | {r['violation_pooled']:.3f} "
                 f"[{r['violation_wilson'][0]:.3f}, {r['violation_wilson'][1]:.3f}] | "
                 f"{r['success_pooled']:.3f} | {f(r.get('error_median'))} | {f(r.get('max_dose_frac_mean'))} | "
                 f"{f(r.get('cowardice_rate'))} | {f(r.get('risk_sharing_mean'))} |")
print("\n".join(lines))
if a.out:
    with open(a.out, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    json.dump(rows, open(a.out.replace(".md", ".json"), "w"), indent=1)
