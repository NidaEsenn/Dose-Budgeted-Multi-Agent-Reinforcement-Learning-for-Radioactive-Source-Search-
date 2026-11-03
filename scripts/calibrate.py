"""AC-3 calibration (week 5): violation rate of dose-unaware search vs budget.

For a dose-unaware policy the dose it receives does not depend on the budget,
so one run with an effectively infinite budget yields the whole curve
P(max robot dose >= b) for every budget b (no re-runs per budget level).
The target is a budget at which dose-unaware search violates in >= 30 % of
episodes (AC-3). Re-run with the trained unconstrained MAPPO policy
(``--policy checkpoint:<path>``) once available -- AC-3 is defined on MAPPO.

    python scripts/calibrate.py --episodes 96 --out docs/results/calibration.json
"""
import argparse
import json

import numpy as np

from radsearch.baselines import make_baseline
from radsearch.env import EnvConfig
from radsearch.eval.runner import run_episodes

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=96)
    ap.add_argument("--policies", default="approach,greedy")
    ap.add_argument("--isotopes", default="Cs-137,Co-60")
    ap.add_argument("--activity", default="1,100")
    ap.add_argument("--budgets", default="0.05,0.1,0.2,0.3,0.5,1.0,2.0")
    ap.add_argument("--particles", type=int, default=1000)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    lo, hi = map(float, a.activity.split(","))
    budgets = np.array([float(b) for b in a.budgets.split(",")])
    rows = []
    for pol in a.policies.split(","):
        for iso in a.isotopes.split(","):
            cfg = EnvConfig(isotope=iso, activity_TBq=(lo, hi), budget_base_Gy=1e6,
                            n_particles=a.particles, model_error="field", model_error_sigma=0.3)
            if pol.startswith("checkpoint:"):
                from radsearch.algos.policy import load_policy
                policy = load_policy(pol.split(":", 1)[1])
            else:
                policy = make_baseline(pol, **({"beta": 0.0} if pol == "greedy" else {}))
            eps = run_episodes(policy, cfg, list(range(a.episodes)))
            maxd = np.array([e["max_dose"] for e in eps])
            row = dict(policy=pol, isotope=iso, activity_TBq=[lo, hi],
                       success=float(np.mean([e["success"] for e in eps])),
                       steps=float(np.mean([e["steps"] for e in eps])),
                       max_dose_median=float(np.median(maxd)),
                       max_dose_p90=float(np.percentile(maxd, 90)),
                       violation_vs_budget={f"{b:g}": float((maxd >= b).mean()) for b in budgets})
            rows.append(row)
            print(json.dumps(row), flush=True)
    if a.out:
        json.dump(rows, open(a.out, "w"), indent=1)
