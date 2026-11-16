"""Headroom test (FORMULATION.md Q6): how much better than the reference rule can a
policy be at the same safety level?

    python scripts/headroom.py sweep  --out docs/results/headroom_sweep.json   # validation seeds
    python scripts/headroom.py final  --out docs/results/headroom_final.json   # test seeds, best configs

Sweep: greedy dose weight (beta) x crowd penalty x reserve quantile, on 300 VALIDATION
missions (seeds 20,000,000+), so the test set is not used for tuning. The best config
with violations <= 5 % is then evaluated on the same 1000 TEST missions as P1, together
with the clairvoyant bound (reserve layer using the true dose: not deployable).
"""
import argparse
import concurrent.futures as cf
import itertools
import json

from radsearch.evaluate import evaluate_policy, load_env_cfg, make_policy
from radsearch.eval.runner import TEST_SEED_BASE

VAL_BASE = 20_000_000
KEYS = ["success_rate", "success_ci", "violation_rate", "violation_ci", "stranded_rate",
        "wrong_declare_rate", "steps_mean", "team_dose_mean", "withdraw_rate"]


def one(spec, n, base):
    m = evaluate_policy(make_policy(spec), load_env_cfg(None), n, seed_base=base, keep_episodes=False)["metrics"]
    return spec, {k: m[k] for k in KEYS}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["sweep", "final"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--best", default=None, help="final: spec of the tuned rule")
    a = ap.parse_args()
    if a.stage == "sweep":
        specs = [f"baseline:greedy+withdraw,beta={b},crowd_penalty={c},wd_quantile={q}"
                 for b, c, q in itertools.product([0.0, 0.3, 1.0, 3.0], [0.0, 0.5, 1.0], [0.9, 0.97])]
        specs.append("baseline:greedy+withdraw_oracle")
        n, base = 300, VAL_BASE
    else:
        specs = [a.best, "baseline:greedy+withdraw_oracle",
                 "baseline:greedy+withdraw_oracle,beta=0.0", "baseline:greedy+withdraw_oracle,beta=0.3"]
        n, base = 1000, TEST_SEED_BASE
    res = {}
    with cf.ProcessPoolExecutor(a.workers) as ex:
        for spec, m in ex.map(one, specs, [n] * len(specs), [base] * len(specs)):
            res[spec] = m
            print(f"{spec:75s} succ {m['success_rate']:.3f} viol {m['violation_rate']:.3f} "
                  f"strand {m['stranded_rate']:.3f} wrong {m['wrong_declare_rate']:.3f} steps {m['steps_mean']:.1f}",
                  flush=True)
            json.dump(dict(stage=a.stage, n=n, seed_base=base, results=res), open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
