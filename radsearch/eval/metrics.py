"""Metric definitions of Section 8.1 and confidence intervals (FR-EVAL-03)."""
from __future__ import annotations

import numpy as np
from scipy import stats


def wilson_interval(k: int, n: int, conf: float = 0.95):
    """Wilson score interval for a binomial proportion (violation rates)."""
    if n == 0:
        return (float("nan"), float("nan"))
    z = stats.norm.ppf(0.5 + conf / 2)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (float(c - h), float(c + h))


def risk_sharing_score(budget, dose) -> float:
    """Spearman correlation between each robot's budget and its share of team dose."""
    budget, dose = np.asarray(budget), np.asarray(dose)
    if np.ptp(budget) == 0 or dose.sum() <= 0 or np.ptp(dose) == 0:
        return float("nan")
    return float(stats.spearmanr(budget, dose / dose.sum()).statistic)


def episode_metrics(episodes: list[dict], cowardice_fraction: float = 0.1) -> dict:
    n = len(episodes)
    if n == 0:
        return {}
    anyv = np.array([e["any_violation"] for e in episodes])
    perv = np.array([e["violated"] for e in episodes], float)
    succ = np.array([e["success"] for e in episodes])
    err = np.array([e["error"] for e in episodes])
    ttl = np.array([e["time_to_localize"] for e in episodes])
    maxd = np.array([e["max_dose"] for e in episodes])
    team = np.array([e["team_dose"] for e in episodes])
    maxfrac = np.array([e["max_rate_frac"] for e in episodes])
    dose_frac = np.array([np.max(np.array(e["dose"]) / np.array(e["budget"])) for e in episodes])
    failed = ~succ
    cow = float((maxfrac[failed] < cowardice_fraction).mean()) if failed.any() else 0.0
    rs = np.array([risk_sharing_score(e["budget"], e["dose"]) for e in episodes])
    k = int(anyv.sum())
    return dict(
        n_episodes=n,
        violation_rate=k / n, violation_ci=wilson_interval(k, n),
        per_robot_violation=perv.mean(0).tolist(),
        success_rate=float(succ.mean()), success_ci=wilson_interval(int(succ.sum()), n),
        error_median=float(np.median(err)),
        error_iqr=[float(np.percentile(err, 25)), float(np.percentile(err, 75))],
        time_to_localize_mean=float(ttl.mean()),
        max_dose_mean=float(maxd.mean()), team_dose_mean=float(team.mean()),
        max_dose_frac_mean=float(dose_frac.mean()),
        cowardice_rate=cow,
        risk_sharing_mean=float(np.nanmean(rs)) if np.isfinite(rs).any() else float("nan"),
        steps_mean=float(np.mean([e["steps"] for e in episodes])),
        stranded_rate=float(np.mean([e.get("any_stranded", False) for e in episodes])),
        return_mean=float(np.mean([e["ret"] for e in episodes])),
        **_calibration_metrics(episodes),
    )


def _calibration_metrics(episodes: list[dict]) -> dict:
    """K1.3 / K1.1: declaration quality, posterior calibration, information per dose."""
    if not episodes or "maha2" not in episodes[0]:
        return {}
    conf = np.array([e["confident"] for e in episodes])
    wrong = np.array([e["wrong_declare"] for e in episodes])
    info = np.array([0.5 * (e["logdet0"] - e["logdet"]) for e in episodes])   # nats
    team = np.array([e["team_dose"] for e in episodes])
    return dict(
        declare_rate=float(conf.mean()),
        wrong_declare_rate=float(wrong.mean()),
        wrong_given_declare=float(wrong[conf].mean()) if conf.any() else float("nan"),
        coverage50=float(np.mean([e["covered50"] for e in episodes])),
        coverage90=float(np.mean([e["covered90"] for e in episodes])),
        coverage90_declared=float(np.mean([e["covered90"] for e, c in zip(episodes, conf) if c]))
        if conf.any() else float("nan"),
        info_gain_mean=float(info.mean()),
        info_per_Gy=float(info.sum() / max(team.sum(), 1e-12)),
        withdraw_rate=float(np.mean([any(e.get("withdrawn", [])) for e in episodes])),
    )


def pareto_front(points: np.ndarray) -> np.ndarray:
    """Indices of non-dominated points when *minimising* both columns
    (e.g. localisation error and dose)."""
    pts = np.asarray(points, float)
    keep = []
    for i, p in enumerate(pts):
        dominated = np.any(np.all(pts <= p, 1) & np.any(pts < p, 1))
        if not dominated:
            keep.append(i)
    return np.array(keep, int)


def aggregate_over_seeds(per_seed_scores: np.ndarray, reps: int = 2000, seed: int = 0) -> dict:
    """IQM with stratified-bootstrap 95 % CI over training seeds (rliable).

    per_seed_scores: (n_seeds, n_tasks) -- e.g. one column per test setting.
    """
    from rliable import library as rly
    from rliable import metrics as rlm
    scores = {"m": np.atleast_2d(np.asarray(per_seed_scores, float))}
    agg, ci = rly.get_interval_estimates(
        scores, lambda x: np.array([rlm.aggregate_iqm(x), rlm.aggregate_mean(x)]), reps=reps)
    return dict(iqm=float(agg["m"][0]), iqm_ci=ci["m"][:, 0].tolist(),
                mean=float(agg["m"][1]), mean_ci=ci["m"][:, 1].tolist())
