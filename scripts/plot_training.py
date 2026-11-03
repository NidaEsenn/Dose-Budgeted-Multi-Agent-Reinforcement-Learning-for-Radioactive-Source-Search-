"""Learning curves (key figure): success, violation, max dose/budget, lambda, length.

    python scripts/plot_training.py runs/E1/mappo/n4/seed0 runs/E1/mappo_lag_b/n4/seed0 --out fig.png

One measure per panel (no dual axes); series colours follow a fixed
categorical order (validated palette); curves are moving averages.
"""
import argparse
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
INK, MUTED, GRID = "#1a1a19", "#6b6a63", "#e6e5e0"


def load(run):
    rows = [json.loads(l) for l in open(os.path.join(run, "metrics.jsonl"))]
    return {k: np.array([r[k] for r in rows], dtype=object) for k in rows[0]}


def smooth(y, k=15):
    y = np.asarray(y, float)
    if len(y) < k:
        return y
    c = np.cumsum(np.insert(y, 0, 0.0))
    out = (c[k:] - c[:-k]) / k
    return np.concatenate([np.full(k - 1, np.nan), out])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--labels", nargs="*")
    ap.add_argument("--out", default="learning_curves.png")
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    labels = a.labels or [r.rstrip("/").split("/")[-3] for r in a.runs]
    panels = [("success", "success rate"), ("violation", "budget-violation rate"),
              ("max_dose_frac", "max robot dose / budget"), ("lam", "Lagrange multiplier λ (per robot)"),
              ("ep_len", "episode length [steps]")]
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK})
    fig, axes = plt.subplots(1, len(panels), figsize=(3.1 * len(panels), 2.8), dpi=150)
    for i, (run, lab) in enumerate(zip(a.runs, labels)):
        d = load(run)
        x = d["env_steps"].astype(float) / 1e3
        for ax, (key, title) in zip(axes, panels):
            if key == "lam":
                lam = np.array([list(v) for v in d["lam"]], float)
                if np.allclose(lam, 0) and "lag" not in lab:
                    continue
                for j in range(lam.shape[1]):
                    ax.plot(x, smooth(lam[:, j]), color=SERIES[i], lw=2 if j == 0 else 1,
                            alpha=1.0 if j == 0 else 0.55, label=lab if j == 0 else None)
            else:
                ax.plot(x, smooth(d[key].astype(float)), color=SERIES[i], lw=2, label=lab)
    for ax, (key, title) in zip(axes, panels):
        ax.set_title(title, fontsize=9, loc="left", color=INK)
        ax.set_xlabel("env steps [k]")
        ax.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[1].axhline(0.05, color=MUTED, lw=1, ls="--")
    axes[1].text(axes[1].get_xlim()[0], 0.05, " 5 % target", va="bottom", fontsize=7, color=MUTED)
    axes[0].legend(frameon=False, fontsize=8)
    if a.title:
        fig.suptitle(a.title, fontsize=10, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(a.out, bbox_inches="tight")
    print("wrote", a.out)
