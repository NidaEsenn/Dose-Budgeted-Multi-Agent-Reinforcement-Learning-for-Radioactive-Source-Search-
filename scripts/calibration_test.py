"""Dose-calibration test of the reserve safety layer (FORMULATION.md, Q2/Q4).

At every decision of every robot that stays in the field, compare the safety layer's
prediction of (next-step dose + exit dose from the next cell), made from J posterior
particles, with the TRUE value computed from the real source. If the posterior is
calibrated, the true value exceeds the q-quantile of the J samples with probability
about 1 - q (and exceeds the maximum of J i.i.d. samples with probability 1/(J+1)).

    python scripts/calibration_test.py --episodes 300 --out docs/results/calibration_dose.json

The policy is the reference rule (greedy + reserve withdraw, q = 0.97, 32 particles),
re-implemented here so the prediction and the action use the same particle draw.
"""
import argparse
import json

import numpy as np

from radsearch import physics as P
from radsearch.baselines import make_baseline
from radsearch.env import RadSearchCore
from radsearch.eval.metrics import wilson_interval
from radsearch.eval.runner import TEST_SEED_BASE
from radsearch.evaluate import load_env_cfg
from radsearch.shield import candidate_cells, predictive_fields
from radsearch.world import N_ACTIONS, WITHDRAW

LEVELS = [0.5, 0.8, 0.9, 0.95, 0.97]


def true_step_field(core, b):
    cfg = core.cfg
    rate = core.true_dose_rate(b, core._cell_xy).reshape(cfg.width, cfg.height)
    return P.step_dose(rate, cfg.step_time)


def run(cfg, seeds, q=0.97, J=32, batch=16, rng_seed=0):
    rng = np.random.default_rng(rng_seed)
    base = make_baseline("greedy")
    rows = []          # one per (robot, decision) that moves in the field
    eps_out = []
    for start in range(0, len(seeds), batch):
        chunk = seeds[start:start + batch]
        core = RadSearchCore(cfg, len(chunk), autoreset=False)
        for j, s in enumerate(chunk):
            core.reset_env(j, seed=s)
        tstep = np.stack([true_step_field(core, j) for j in range(len(chunk))])     # (B,W,H)
        ttot = tstep + core.exit_true                                                # true step+exit per cell
        live = np.ones(len(chunk), bool)
        while live.any():
            step, exitc = predictive_fields(core, J, rng)                            # (B,J,W,H)
            tot = step + exitc
            cand = candidate_cells(core)                                             # (B,N,5,2)
            act = np.asarray(base.act(core)).copy()
            a5 = np.minimum(act, N_ACTIONS - 1)
            bi = np.arange(core.B)[:, None]
            cell = cand[bi, np.arange(core.N)[None], a5]                             # (B,N,2)
            samp = tot[bi[..., None], np.arange(J)[None, None], cell[..., 0][..., None], cell[..., 1][..., None]]
            samp = np.transpose(samp, (0, 1, 2)) if samp.ndim == 3 else samp         # (B,N,J)
            with np.errstate(invalid="ignore"):
                qv = np.quantile(samp, q, axis=-1)
            over = core.active & (core.dose + np.nan_to_num(qv, nan=np.inf) > core.budget)
            act[over] = WITHDRAW
            truth = ttot[bi, cell[..., 0], cell[..., 1]]                             # (B,N)
            for b in range(core.B):
                if not live[b]:
                    continue
                for i in range(core.N):
                    if core.active[b, i] and not over[b, i]:
                        s = samp[b, i]
                        if not np.all(np.isfinite(s)) or not np.isfinite(truth[b, i]):
                            continue
                        rows.append(dict(
                            seed=int(chunk[b]), t=int(core.t[b]), robot=i, truth=float(truth[b, i]),
                            pit=float(np.mean(s <= truth[b, i])),
                            above={str(l): bool(truth[b, i] > np.quantile(s, l)) for l in LEVELS},
                            above_max=bool(truth[b, i] > s.max()), above_mean=bool(truth[b, i] > s.mean()),
                            near_limit=bool(core.dose[b, i] + qv[b, i] > 0.5 * core.budget[b, i]),
                            margin_frac=float((core.dose[b, i] + truth[b, i]) / core.budget[b, i]),
                            rel_err_q=float(truth[b, i] / max(qv[b, i], 1e-15)),
                            logA_true=float(core.logA[b])))
            out = core.step(act)
            for ep in out["episodes"]:
                j = chunk.index(ep["seed"])
                if live[j]:
                    eps_out.append(ep)
                    live[j] = False
            core.t[~live] = 0
            core.active[~live] = False
    return rows, eps_out


def summarise(rows, sel=None):
    r = [x for x in rows if sel is None or sel(x)]
    n = len(r)
    if n == 0:
        return dict(n=0)
    res = dict(n=n)
    for l in LEVELS:
        k = sum(x["above"][str(l)] for x in r)
        res[f"exceed_q{l}"] = dict(observed=k / n, nominal=1 - l, ci=wilson_interval(k, n))
    k = sum(x["above_max"] for x in r)
    res["exceed_max"] = dict(observed=k / n, nominal_if_calibrated=1 / 33, ci=wilson_interval(k, n))
    res["exceed_mean"] = sum(x["above_mean"] for x in r) / n
    pit = np.array([x["pit"] for x in r])
    res["pit_hist"] = np.histogram(pit, bins=10, range=(0, 1))[0].tolist()
    res["ratio_truth_over_q97_p95"] = float(np.percentile([x["rel_err_q"] for x in r], 95))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=300)
    ap.add_argument("--out", default="docs/results/calibration_dose.json")
    ap.add_argument("--set", nargs="*", default=[])
    a = ap.parse_args()
    cfg = load_env_cfg(None, a.set)
    seeds = [TEST_SEED_BASE + i for i in range(a.episodes)]
    rows, eps = run(cfg, seeds)
    early = lambda x: x["t"] < 6
    res = dict(
        note="Reference rule (greedy + reserve withdraw, q=0.97, 32 particles); prediction = next-step + exit dose "
             "from the chosen next cell, per posterior particle; truth from the real source.",
        overrides=a.set, missions=len(eps),
        violation_rate=float(np.mean([e["any_violation"] for e in eps])),
        success_rate=float(np.mean([e["success"] for e in eps])),
        all=summarise(rows),
        near_limit=summarise(rows, lambda x: x["near_limit"]),
        early_steps=summarise(rows, early),
        later_steps=summarise(rows, lambda x: not early(x)),
        strong_source=summarise(rows, lambda x: x["logA_true"] > np.log10(50e12)),
        weaker_source=summarise(rows, lambda x: x["logA_true"] <= np.log10(50e12)),
    )
    json.dump(res, open(a.out, "w"), indent=1)
    for k in ("all", "near_limit", "early_steps", "later_steps", "strong_source", "weaker_source"):
        s = res[k]
        if s.get("n"):
            print(f"{k:14s} n={s['n']:6d}  P(true>q97)={s['exceed_q0.97']['observed']:.3f} "
                  f"[{s['exceed_q0.97']['ci'][0]:.3f},{s['exceed_q0.97']['ci'][1]:.3f}] (nominal 0.03) | "
                  f">q90 {s['exceed_q0.9']['observed']:.3f} (0.10) | >q50 {s['exceed_q0.5']['observed']:.3f} (0.50) | "
                  f">max {s['exceed_max']['observed']:.3f} (0.030) | >mean {s['exceed_mean']:.3f}")
    print("missions", res["missions"], "violation", res["violation_rate"], "success", res["success_rate"])


if __name__ == "__main__":
    main()
