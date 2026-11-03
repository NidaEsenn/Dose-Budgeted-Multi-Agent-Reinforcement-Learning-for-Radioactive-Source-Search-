"""AC-2 / FR-EST-04: test the particle filter alone, without any learning.

Random-walk robots in a room; compares PF variants on final localisation
error, success (< 1 m), calibration (truth inside the 95 % ellipse) and time.

    python scripts/eval_estimator.py --episodes 64 --obstacles 0
"""
import argparse
import json
import time

import numpy as np

from radsearch import physics as P
from radsearch.estimator import ParticleFilter
from radsearch.world import MOVES, generate_layout, sample_source


def run(variant, episodes, n_agents, steps, n_particles, obstacles, isotope, seed0, batch=16):
    iso = P.Isotope.from_constants(isotope)
    det = P.Detector.from_constants()
    dwell = 10.0
    errs, inside95, sig = [], [], []
    t0 = time.perf_counter()
    for start in range(0, episodes, batch):
        B = min(batch, episodes - start)
        pf = ParticleFilter(B, n_particles, iso, det, dwell, variant=variant)
        rngs = [np.random.default_rng(seed0 + start + b) for b in range(B)]
        lays = [generate_layout(r, n_agents, n_obstacles=obstacles) for r in rngs]
        K = max(1, max(len(l.rects) for l in lays))
        rects = np.zeros((B, K, 4)); mu = np.zeros((B, K)); nrect = np.zeros(B, int)
        for b, l in enumerate(lays):
            k = len(l.rects); nrect[b] = k
            rects[b, :k] = l.rects
            mu[b, :k] = [iso.mu_material[m] for m in l.materials]
        pf.set_geometry(rects, mu, nrect)
        src = np.stack([sample_source(r, l) for r, l in zip(rngs, lays)])
        logA = np.array([r.uniform(12, 14) for r in rngs])
        cells = np.stack([l.start_cells for l in lays])
        for b in range(B):
            pf.reset(b, lays[b].occ, 1.0, np.random.default_rng(10_000 + seed0 + start + b))
        for t in range(steps):
            for b in range(B):
                a = rngs[b].integers(5, size=n_agents)
                nxt = cells[b] + MOVES[a]
                W, H = lays[b].occ.shape
                okm = (nxt[:, 0] >= 0) & (nxt[:, 0] < W) & (nxt[:, 1] >= 0) & (nxt[:, 1] < H)
                nxt = np.where(okm[:, None], nxt, cells[b])
                okm = ~lays[b].occ[nxt[:, 0], nxt[:, 1]]
                cells[b] = np.where(okm[:, None], nxt, cells[b])
            xy = cells + 0.5
            from radsearch._kernels import tau_bpn
            tau = tau_bpn(src[:, None], xy, rects, mu, nrect, det.height)[:, 0]
            lam = P.expected_counts(src[:, None], 10 ** logA[:, None], xy, iso, det, dwell, tau)
            k = np.stack([rngs[b].poisson(lam[b]) for b in range(B)])
            pf.update(xy, k, np.ones((B, n_agents)))
        mean, cov = pf.estimate()
        for b in range(B):
            e = mean[b, :2] - src[b]
            errs.append(float(np.linalg.norm(e)))
            c = cov[b, :2, :2] + 1e-9 * np.eye(2)
            inside95.append(float(e @ np.linalg.solve(c, e)) <= 5.991)
            sig.append(float(np.sqrt(np.linalg.eigvalsh(c)[-1])))
    dt = time.perf_counter() - t0
    errs = np.array(errs)
    return dict(variant=variant, median_err=float(np.median(errs)),
                iqr=[float(np.percentile(errs, 25)), float(np.percentile(errs, 75))],
                success=float((errs < 1.0).mean()), calib95=float(np.mean(inside95)),
                median_sigma=float(np.median(sig)),
                ms_per_env_step=1e3 * dt / (episodes * steps))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=64)
    ap.add_argument("--agents", type=int, default=4)
    ap.add_argument("--steps", type=int, default=100)
    ap.add_argument("--particles", type=int, default=2000)
    ap.add_argument("--obstacles", type=int, default=0)
    ap.add_argument("--isotope", default="Cs-137")
    ap.add_argument("--variants", default="sir,rpf,tempered")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = [run(v, a.episodes, a.agents, a.steps, a.particles, a.obstacles, a.isotope, a.seed)
           for v in a.variants.split(",")]
    for r in res:
        print(json.dumps(r))
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)
