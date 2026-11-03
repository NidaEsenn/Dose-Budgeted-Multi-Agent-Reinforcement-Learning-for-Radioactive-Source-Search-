"""D6: which measurement-noise model yields a genuine dose/information trade-off?

For each noise model, compare a far-field strategy (perimeter) with a
near-field one (approach) and the dose-unaware greedy seeker. A trade-off
exists when near-field search localises better *and* costs more dose.
"""
import argparse, json, itertools
import numpy as np
from radsearch.baselines import make_baseline
from radsearch.env import EnvConfig
from radsearch.eval.metrics import episode_metrics
from radsearch.eval.runner import run_episodes

ap = argparse.ArgumentParser()
ap.add_argument("--episodes", type=int, default=48)
ap.add_argument("--isotope", default="Cs-137")
ap.add_argument("--models", default="none:0,iid:0.2,field:0.2,field:0.3")
ap.add_argument("--policies", default="perimeter,approach,greedy")
ap.add_argument("--confident", type=int, default=1)
ap.add_argument("--out", default=None)
a = ap.parse_args()
rows = []
for model, pol in itertools.product(a.models.split(","), a.policies.split(",")):
    mode, sig = model.split(":")
    cfg = EnvConfig(isotope=a.isotope, model_error=mode, model_error_sigma=float(sig),
                    n_particles=1000, terminate_on_confident=bool(a.confident), budget_base_Gy=1.0)
    eps = run_episodes(make_baseline(pol, **({"beta": 0.0} if pol == "greedy" else {})), cfg,
                       list(range(a.episodes)))
    m = episode_metrics(eps)
    row = dict(model=model, policy=pol, success=m["success_rate"], err=m["error_median"],
               steps=m["steps_mean"], violation=m["violation_rate"],
               max_dose_frac=m["max_dose_frac_mean"],
               min_dist=float(np.median([e["min_source_dist"] for e in eps])))
    rows.append(row)
    print(json.dumps({k: round(v, 3) if isinstance(v, float) else v for k, v in row.items()}), flush=True)
if a.out:
    json.dump(rows, open(a.out, "w"), indent=1)
