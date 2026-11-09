"""Real-simulator figures for the midterm deck (current rules, greedy + reserve withdraw rule).

    python scripts/make_figures_midterm.py   ->  docs/figures/dose_trace.png, particles.png
"""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

from radsearch.evaluate import load_env_cfg
from radsearch.env import RadSearchCore
from radsearch.baselines import make_baseline
from radsearch.eval.runner import TEST_SEED_BASE
from radsearch.shield import candidate_cells
from radsearch.render import dose_rate_map

cfg = load_env_cfg(None)
INK, MUTED, ORANGE, BLUE, RED = "#14213D", "#4A5568", "#E8833A", "#3A6EA5", "#B5401E"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": INK, "axes.labelcolor": INK,
                     "xtick.color": INK, "ytick.color": INK})


def run(seed):
    core = RadSearchCore(cfg, 1, autoreset=False)
    core.reset_env(0, seed=seed)
    wd = make_baseline("greedy+withdraw", wd_quantile=0.97)
    log = dict(dose=[core.dose[0].copy()], pred=[], act=[], cells=[core.cells[0].copy()],
               parts=[core.pf.subsample(0, 600, np.random.default_rng(0)).copy()], active=[core.active[0].copy()])
    while True:
        pred = wd.predicted(core)                                    # (1,N,5) q97 next+exit
        act = np.asarray(wd.base.act(core)).copy()
        chosen = np.take_along_axis(pred, np.minimum(act, 4)[..., None], -1)[..., 0]
        over = core.active & (core.dose + np.nan_to_num(chosen, nan=np.inf) > core.budget)
        act[over] = 5
        log["pred"].append(np.where(core.active[0], core.dose[0] + chosen[0], np.nan))
        log["act"].append(act[0].copy())
        out = core.step(act)
        log["dose"].append(core.dose[0].copy()); log["cells"].append(core.cells[0].copy())
        log["active"].append(core.active[0].copy())
        log["parts"].append(core.pf.subsample(0, 600, np.random.default_rng(len(log["parts"]))).copy())
        if out["done"][0]:
            return core, log, out["episodes"][0]


# pick the first test mission where a robot withdraws, nobody violates, and the team succeeds
for i in range(200):
    core, log, ep = run(TEST_SEED_BASE + i)
    if any(ep["withdrawn"]) and not ep["any_violation"] and ep["success"] and ep["confident"] and 10 <= ep["steps"] <= 60 and min(ep["dose"]) > 0 \
            and ep["n_obstacles"] >= 3 and ep["withdraw_step"][int(np.flatnonzero(ep["withdrawn"])[0])] < ep["steps"] - 3:
        break
print("mission", i, "seed", ep["seed"], "steps", ep["steps"], "withdrawn", ep["withdrawn"],
      "dose", np.round(ep["dose"], 4), "error", round(ep["error"], 2), "activity TBq", round(ep["activity_TBq"], 1))
r = int(np.flatnonzero(ep["withdrawn"])[0])
dose = np.array(log["dose"])[:, r]
pred = np.array(log["pred"])[:, r]
wstep = int(ep["withdraw_step"][r])
T = len(dose) - 1
t = np.arange(T + 1) * cfg.step_time / 60          # minutes

# ---- figure 1: dose trace of the withdrawing robot
fig, ax = plt.subplots(figsize=(9.5, 5.6), dpi=220)
plt.rcParams.update({"font.size": 17})
ax.tick_params(labelsize=16)
B = core.budget[0, r]
ax.axhline(B, color=RED, ls="--", lw=2.2)
ax.text(t[0], B * 1.015, f"Budget {B:.1f} Gy", color=RED, fontsize=17, fontweight="bold", va="bottom")
tp = t[:wstep + 1]
pp = pred[:wstep + 1]
ax.fill_between(tp, dose[:wstep + 1], np.minimum(pp, B * 1.1), color=ORANGE, alpha=0.25, lw=0)
pp = np.minimum(pp, B * 1.1)
ax.plot(tp, pp, color=ORANGE, lw=2.4, ls=(0, (5, 2)), label="Checked: used + next step + exit")
# dose up to the withdraw decision, the exit dose as a vertical jump, then flat
td = np.r_[t[:wstep + 1], t[wstep], t[-1]]
dd = np.r_[dose[:wstep + 1], dose[wstep + 1], dose[-1]]
ax.plot(td, dd, color=INK, lw=3, label="Dose received (true field)")
ax.annotate("prediction would exceed\nthe budget: withdraw", xy=(t[wstep], B * 1.0), xytext=(0.15, B * 0.42),
            color=ORANGE, fontsize=16, fontweight="bold", arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.8))
ax.axvline(t[wstep], color=BLUE, lw=2)
ax.text(t[wstep] + 0.06, dose[wstep + 1] + B * 0.04, "exit dose added,\nrobot is out", color=BLUE, fontsize=16, fontweight="bold")
ax.set_xlabel("Mission time (min) · one decision every 10 s", fontsize=17)
ax.set_ylabel("Cumulative dose (Gy)", fontsize=17)
ax.set_ylim(0, B * 1.12); ax.set_xlim(0, t[-1] + 0.1)
ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.80), frameon=False, fontsize=15)
fig.tight_layout(); fig.savefig("docs/figures/dose_trace.png"); plt.close(fig)

# ---- figure 2: particle snapshots
_, _, rate = dose_rate_map(core, 0, 0.1)
W, H = cfg.width * cfg.cell, cfg.height * cfg.cell
k_mid = max(1, T // 2)
snaps = [(0, "Start: no information"), (k_mid, f"After {k_mid * 10 / 60:.1f} min: narrowing down"), (T, f"End ({T * 10 / 60:.1f} min): declared")]
fig, axs = plt.subplots(1, 3, figsize=(15, 5.4), dpi=200)
for ax, (k, title) in zip(axs, snaps):
    ax.imshow(rate.T, origin="lower", extent=(0, W, 0, H), cmap="magma", norm=LogNorm(rate.max() * 1e-5, rate.max()), alpha=0.85)
    for (x0, y0, x1, y1) in core.layouts[0].rects:
        ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, color="#9AA5B1", ec=INK, lw=1))
    p = log["parts"][k]
    ax.scatter(p[:, 0], p[:, 1], s=4, color="#7FD3FF", alpha=0.6, lw=0)
    ax.scatter(*core.src[0], marker="*", s=320, color="#FFD23F", ec=INK, lw=1.2, zorder=5)
    cells = log["cells"][k]; act = log["active"][k]
    for j in range(core.N):
        if act[j] or k == 0:
            ax.scatter((cells[j, 0] + .5) * cfg.cell, (cells[j, 1] + .5) * cfg.cell, s=110, color="#FFFFFF", ec=INK, lw=1.5, zorder=6)
    dx, dy = core.layouts[0].door
    ax.add_patch(plt.Rectangle((dx * cfg.cell, dy * cfg.cell), cfg.cell, cfg.cell, color="#3FD18A", alpha=0.9, zorder=4))
    ax.set_title(title, color=INK, fontsize=15, fontweight="bold")
    ax.set_xticks([]); ax.set_yticks([]); ax.set_xlim(0, W); ax.set_ylim(0, H)
    for s in ax.spines.values(): s.set_visible(True); s.set_color(INK); s.set_linewidth(2)
fig.tight_layout(); fig.savefig("docs/figures/particles.png"); plt.close(fig)
json.dump(dict(seed=ep["seed"], steps=ep["steps"], robot=r, withdraw_step=wstep, dose=ep["dose"], budget=ep["budget"],
               error=ep["error"], activity_TBq=ep["activity_TBq"], success=ep["success"]),
          open("docs/figures/midterm_figures_mission.json", "w"), indent=1)
