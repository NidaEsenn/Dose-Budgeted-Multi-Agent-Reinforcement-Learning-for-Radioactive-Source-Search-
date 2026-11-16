"""Algorithm figures for the midterm deck, from one real test mission (current rules).

    python scripts/make_figures_algorithms.py
      -> docs/figures/alg_filter.png    particle-filter loop + convergence of the estimate
         docs/figures/alg_reserve.png   how the reserve check decides (map + 32 predictions)
         docs/figures/alg_policy.png    MAPPO / CTDE diagram (schematic)

The policy is the reference rule (greedy + reserve withdraw, q = 0.97, 32 particles),
re-implemented so the plotted samples are exactly the ones the check used.
"""
import json

import matplotlib
import numpy as np
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from radsearch.baselines import make_baseline
from radsearch.env import RadSearchCore
from radsearch.evaluate import load_env_cfg
from radsearch.render import dose_rate_map
from radsearch.shield import candidate_cells, predictive_fields
from radsearch.world import N_ACTIONS, WITHDRAW

SEED, Q, J = 10000034, 0.97, 32
INK, MUTED, BLUE, ORANGE, GREY, RED, GREEN = "#14213D", "#4A5568", "#2F6FB3", "#E0871F", "#9AA5B1", "#B5401E", "#2E9E6A"
LIGHT = "#F3F4F6"
plt.rcParams.update({"font.family": "Inter", "font.size": 14, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": INK, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK})
cfg = load_env_cfg(None)


def run():
    core = RadSearchCore(cfg, 1, autoreset=False)
    core.reset_env(0, seed=SEED)
    base = make_baseline("greedy")
    log = []
    k = 0
    while True:
        mean, cov = core.pf.estimate()
        rec = dict(t=int(core.t[0]), mean=mean[0].copy(), sd=np.sqrt(np.diag(cov[0])).copy(),
                   psig=float(core.pf.position_sigma()[0]), dose=core.dose[0].copy(),
                   cells=core.cells[0].copy(), active=core.active[0].copy())
        parts = core.pf.subsample(0, J, np.random.default_rng(1000 + k))
        step, exitc = predictive_fields(core, J, np.random.default_rng(1000 + k))
        tot = (step + exitc)[0]                                           # (J,W,H)
        cand = candidate_cells(core)[0]                                   # (N,5,2)
        act = np.asarray(base.act(core)).copy()
        a5 = np.minimum(act[0], N_ACTIONS - 1)
        cell = cand[np.arange(core.N), a5]                                # (N,2)
        samp = tot[:, cell[:, 0], cell[:, 1]].T                           # (N,J)
        with np.errstate(invalid="ignore"):
            qv = np.quantile(samp, Q, axis=-1)
        over = core.active[0] & (core.dose[0] + np.nan_to_num(qv, nan=np.inf) > core.budget[0])
        act[0, over] = WITHDRAW
        rec.update(parts=parts, samp=samp, qv=qv, over=over, cell=cell, step_mean=step[0].mean(0), act=act[0].copy())
        log.append(rec)
        out = core.step(act)
        k += 1
        if out["done"][0]:
            return core, log, out["episodes"][0]


core, log, ep = run()
print("steps", ep["steps"], "withdrawn", ep["withdrawn"], "success", ep["success"], "violation", ep["any_violation"],
      "dose", np.round(ep["dose"], 4))

# ------------------------------------------------------------------ reserve figure
dec = [(k, i) for k, r in enumerate(log) for i in range(core.N) if r["over"][i]]
kw, r = dec[0]                                                       # first withdraw decision
# an earlier, allowed decision of the same robot, with a clearly safe margin
allowed = [k for k in range(kw) if log[k]["active"][r] and not log[k]["over"][r]]
ka = max(allowed, key=lambda k: (log[k]["dose"][r] + log[k]["qv"][r]) if log[k]["dose"][r] + log[k]["qv"][r] < 0.85 * core.budget[0, r] else -1)
_, _, rate = dose_rate_map(core, 0, 0.1)
Wm, Hm = cfg.width * cfg.cell, cfg.height * cfg.cell
dx, dy = core.layouts[0].door
door_dist = core.door_dist[0]


def exit_path(c, step_mean):
    path = [tuple(c)]
    x, y = c
    while door_dist[x, y] > 0:
        nb = [(x + a, y + b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))
              if 0 <= x + a < cfg.width and 0 <= y + b < cfg.height and door_dist[x + a, y + b] == door_dist[x, y] - 1]
        x, y = min(nb, key=lambda p: step_mean[p])
        path.append((x, y))
    return np.array(path)


fig = plt.figure(figsize=(15, 5.6), dpi=200)
gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1, 1], wspace=0.32)
ax = fig.add_subplot(gs[0])
rec = log[kw]
ax.imshow(rate.T, origin="lower", extent=(0, Wm, 0, Hm), cmap="magma", norm=LogNorm(rate.max() * 1e-5, rate.max()), alpha=0.85)
for (x0, y0, x1, y1) in core.layouts[0].rects:
    ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, color="#9AA5B1", ec=INK, lw=1))
ax.add_patch(plt.Rectangle((dx * cfg.cell, dy * cfg.cell), cfg.cell, cfg.cell, color="#3FD18A", zorder=4))
p = rec["parts"]
ax.scatter(p[:, 0], p[:, 1], s=46, marker="x", color="#7FD3FF", lw=1.6, zorder=5, label="32 sampled sources")
ax.scatter(*core.src[0], marker="*", s=380, color="#FFD23F", ec=INK, lw=1.2, zorder=6, label="true source (unknown)")
c0 = (rec["cells"][r] + .5) * cfg.cell
c1 = (rec["cell"][r] + .5) * cfg.cell
path = (exit_path(rec["cell"][r], rec["step_mean"]) + .5) * cfg.cell
ax.plot(path[:, 0], path[:, 1], color="white", lw=2.4, ls=(0, (3, 2)), zorder=5)
ax.plot([], [], color=INK, lw=2.4, ls=(0, (3, 2)), label="way out to door (green)")
ax.add_patch(FancyArrowPatch(c0, c1, arrowstyle="-|>", mutation_scale=20, color="white", lw=2.5, zorder=7))
ax.scatter(*c0, s=170, color="white", ec=INK, lw=1.8, zorder=8, label="robot")
ax.set_xticks([]); ax.set_yticks([]); ax.set_xlim(0, Wm); ax.set_ylim(0, Hm)
for s in ax.spines.values():
    s.set_visible(True); s.set_color(INK); s.set_linewidth(2)
ax.set_title("① Proposed move + way out,\n     under 32 possible sources", loc="left", fontsize=15, fontweight="bold", color=INK)
leg = ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.30), ncol=2, frameon=False, fontsize=11.5,
                handletextpad=0.3, columnspacing=0.9)

B = core.budget[0, r]
for j, (k, title) in enumerate([(ka, f"② Earlier step (t = {log[ka]['t'] * 10 // 60} min {log[ka]['t'] * 10 % 60:02d} s)"),
                                (kw, f"③ Later step (t = {log[kw]['t'] * 10 // 60} min {log[kw]['t'] * 10 % 60:02d} s)")]):
    a = fig.add_subplot(gs[j + 1])
    rr = log[k]
    used = rr["dose"][r]
    tot = used + rr["samp"][r]
    qv = used + rr["qv"][r]
    lo, hi = 0, max(B * 1.25, tot.max() * 1.05)
    bins = np.linspace(lo, hi, 30)
    a.hist(tot, bins=bins, color=BLUE, alpha=0.85, ec="white")
    a.axvline(used, color=GREY, lw=2.2)
    a.text(used, a.get_ylim()[1] * 0.99, " used", color=MUTED, fontsize=12, va="top", ha="left", fontweight="bold")
    a.axvline(B, color=RED, lw=2.4, ls="--")
    a.text(B, a.get_ylim()[1] * 0.85, " budget", color=RED, fontsize=12, va="top", fontweight="bold")
    a.axvline(qv, color=ORANGE, lw=3)
    a.text(qv, a.get_ylim()[1] * 0.70, " 97th pct", color=ORANGE, fontsize=12, va="top", ha="left", fontweight="bold")
    ok = not rr["over"][r]
    a.text(0.5, -0.24, "under budget → move allowed" if ok else "over budget → WITHDRAW",
           transform=a.transAxes, ha="center", fontsize=15, fontweight="bold", color=GREEN if ok else RED)
    a.set_xlim(lo, hi)
    a.set_xlabel("used + next step + way out (Gy)", fontsize=13)
    a.set_ylabel("samples (of 32)", fontsize=13)
    a.set_title(title, loc="left", fontsize=15, fontweight="bold", color=INK, pad=10)
fig.savefig("docs/figures/alg_reserve.png", bbox_inches="tight", pad_inches=0.12)
plt.close(fig)

# ------------------------------------------------------------------ filter figure
fig = plt.figure(figsize=(15, 5.2), dpi=200)
gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 1, 1], wspace=0.40)
ax = fig.add_subplot(gs[0]); ax.axis("off"); ax.set_xlim(0, 10.8); ax.set_ylim(0, 10)
steps = [("Predict", "2,000 guesses\n(x, y, strength)", BLUE), ("Measure", "each robot counts\nfor 10 s", INK),
         ("Re-weight", "weight guesses by how\nwell they explain counts", ORANGE), ("Resample", "keep likely guesses,\nadd small jitter", GREEN)]
pos = [(2.5, 7.6), (8.2, 7.6), (8.2, 2.4), (2.5, 2.4)]
for (lab, sub, col), (x, y) in zip(steps, pos):
    ax.add_patch(FancyBboxPatch((x - 2.35, y - 1.45), 4.7, 2.9, boxstyle="round,pad=0.05,rounding_size=0.35", fc=LIGHT, ec=col, lw=2.5))
    ax.text(x, y + 0.55, lab, ha="center", va="center", fontsize=16, fontweight="bold", color=col)
    ax.text(x, y - 0.55, sub, ha="center", va="center", fontsize=10.5, color=INK)
for (a0, a1) in [((4.85, 7.6), (5.85, 7.6)), ((8.2, 6.05), (8.2, 3.95)), ((5.85, 2.4), (4.85, 2.4)), ((2.5, 3.95), (2.5, 6.05))]:
    ax.add_patch(FancyArrowPatch(a0, a1, arrowstyle="-|>", mutation_scale=18, color=MUTED, lw=2))
ax.text(5.35, 5.0, "every\n10 s", ha="center", va="center", fontsize=13, color=MUTED, fontweight="bold")
ax.set_title("One filter update", loc="left", fontsize=15, fontweight="bold", color=INK)

t = np.array([x["t"] for x in log]) * cfg.step_time / 60
ps = np.array([x["psig"] for x in log])
a = fig.add_subplot(gs[1])
a.plot(t, ps, color=BLUE, lw=3)
a.axhline(cfg.confident_sigma, color=RED, ls="--", lw=2)
a.set_yscale("log")
a.text(t[-1], 0.27, "declare when < 0.3 m", ha="right", va="top", color=RED, fontsize=12, fontweight="bold")
a.set_xlabel("mission time (min)"); a.set_ylabel("position uncertainty σ (m)"); a.set_xticks([0, 1, 2, 3])
a.set_title("Where is it? Uncertainty shrinks", loc="left", fontsize=15, fontweight="bold", color=INK)
a.set_yticks([0.1, 0.3, 1, 3]); a.set_yticklabels(["0.1", "0.3", "1", "3"]); a.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())

m = np.array([x["mean"][2] for x in log]); sd = np.array([x["sd"][2] for x in log])
a = fig.add_subplot(gs[2])
toTBq = lambda la: 10 ** la / 1e12
a.fill_between(t, toTBq(m - sd), toTBq(m + sd), color=ORANGE, alpha=0.25, lw=0, label="estimate ± 1σ")
a.plot(t, toTBq(m), color=ORANGE, lw=3, label="estimate")
a.axhline(ep["activity_TBq"], color=INK, lw=2, ls=":", label="true strength")
a.set_yscale("log"); a.set_xticks([0, 1, 2, 3]); a.set_xlabel("mission time (min)"); a.set_ylabel("source strength (TBq)")
a.set_yticks([10, 20, 50, 100]); a.set_yticklabels(["10", "20", "50", "100"]); a.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
a.legend(frameon=False, fontsize=11.5, loc="upper right")
a.set_title("How strong? Estimate locks on", loc="left", fontsize=15, fontweight="bold", color=INK)
fig.savefig("docs/figures/alg_filter.png", bbox_inches="tight", pad_inches=0.12)
plt.close(fig)

# ------------------------------------------------------------------ policy (CTDE) schematic
fig, ax = plt.subplots(figsize=(10, 5.6), dpi=200)
ax.axis("off"); ax.set_xlim(0, 20); ax.set_ylim(0, 11.2)


def box(x, y, w, h, text, col, fc=LIGHT, fs=13, bold=True, tc=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.3", fc=fc, ec=col, lw=2.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc or INK,
            fontweight="bold" if bold else "normal")


def arrow(a0, a1, col=MUTED, ls="-"):
    ax.add_patch(FancyArrowPatch(a0, a1, arrowstyle="-|>", mutation_scale=16, color=col, lw=1.9, linestyle=ls))


ys = [8.3, 5.1, 1.9]
for i, y in enumerate(ys):
    box(0.2, y, 5.0, 2.0, f"Robot {i + 1} sees: own position,\ncounts, budget left,\nteam estimate, teammates", BLUE, fs=10, bold=False)
    arrow((5.2, y + 1.0), (6.6, 6.1 + (1 - i) * 0.5))
box(6.6, 4.4, 3.6, 3.2, "Shared\npolicy\n(actor)", BLUE, fc="#DCE8F6", fs=15)
box(11.6, 4.4, 3.4, 3.2, "Safety\nlayer\n(mask)", ORANGE, fc="#FBE7CF", fs=15)
arrow((10.2, 6.0), (11.6, 6.0))
ax.text(10.9, 6.35, "action\nprobs", ha="center", va="bottom", fontsize=10, color=MUTED)
box(16.3, 4.4, 3.5, 3.2, "move ↑↓←→\nstay\nwithdraw", INK, fs=13)
arrow((15.0, 6.0), (16.3, 6.0))
box(6.6, 0.4, 8.4, 2.4, "Critic (training only): sees the full\nstate, incl. the true source,\nand scores the team's progress", GREY, fc="#EEF0F3", fs=11, bold=False)
arrow((8.4, 2.8), (8.4, 4.4), col=GREY, ls="--")
ax.text(8.6, 3.55, "PPO update", fontsize=10.5, color=MUTED, va="center")
ax.text(0.2, 10.75, "Train together, act alone (CTDE)", fontsize=15, fontweight="bold", color=INK)
fig.savefig("docs/figures/alg_policy.png", bbox_inches="tight", pad_inches=0.1)
plt.close(fig)

json.dump(dict(seed=SEED, robot=r, allowed_step=int(log[ka]["t"]), withdraw_step=int(log[kw]["t"]),
               steps=ep["steps"], success=ep["success"], violation=ep["any_violation"], dose=ep["dose"]),
          open("docs/figures/alg_figures_mission.json", "w"), indent=1)

# ------------------------------------------------------------------ one-slide overview: estimate -> decide -> check
fig = plt.figure(figsize=(16, 4.6), dpi=200)
gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 1.0, 1.0], wspace=0.16)
# (1) particle filter: start and end snapshots of the same mission (docs/figures/particles.png, make_figures_midterm.py)
pimg = plt.imread("docs/figures/particles.png")
Hh, Ww = pimg.shape[:2]
third = Ww // 3
crop = lambda k: pimg[int(Hh * 0.09):, k * third + 8:(k + 1) * third - 8]
sub = gs[0].subgridspec(1, 2, wspace=0.06)
for j, (k, lab) in enumerate([(0, "start: everywhere"), (2, "end: on the source ★")]):
    a = fig.add_subplot(sub[j]); a.imshow(crop(k)); a.axis("off")
    a.set_title(lab, fontsize=12.5, color=INK)
fig.text(0.125, 0.97, "① Estimate: shared guess (particle filter)", fontsize=15, fontweight="bold", color=BLUE, va="top")

# (2) decide: shared policy, safety mask, actions
a = fig.add_subplot(gs[1]); a.axis("off"); a.set_xlim(0, 10); a.set_ylim(0, 10)


def bx(x, y, w, h, t, col, fc, fs=12, bold=True):
    a.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.3", fc=fc, ec=col, lw=2))
    a.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs, color=INK, fontweight="bold" if bold else "normal")


def ar(p0, p1, col=MUTED, ls="-"):
    a.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=14, color=col, lw=1.8, linestyle=ls))


for i, y in enumerate([7.3, 4.6, 1.9]):
    bx(0.0, y, 2.4, 1.6, f"robot {i + 1}\nown view", BLUE, LIGHT, fs=10.5, bold=False)
    ar((2.4, y + 0.8), (3.4, 5.4))
bx(3.4, 4.0, 2.6, 2.8, "shared\npolicy", BLUE, "#DCE8F6", fs=13)
ar((6.0, 5.4), (6.6, 5.4))
bx(6.6, 4.0, 3.3, 2.8, "move ↑↓←→\nstay\nwithdraw", INK, LIGHT, fs=11.5)
bx(3.4, 0.6, 6.5, 2.1, "trained with a critic that\nsees everything (training only)", GREY, "#EEF0F3", fs=10, bold=False)
ar((4.7, 2.7), (4.7, 4.0), col=GREY, ls="--")
fig.text(0.415, 0.97, "② Decide: greedy rule or MAPPO", fontsize=15, fontweight="bold", color=INK, va="top")

# (3) check: the withdraw decision of the robot above
a = fig.add_subplot(gs[2])
rr = log[kw]; used = rr["dose"][r]; tot = used + rr["samp"][r]; qv = used + rr["qv"][r]; Bd = core.budget[0, r]
a.hist(tot, bins=np.linspace(0, max(Bd * 1.25, tot.max() * 1.05), 26), color=BLUE, alpha=0.85, ec="white")
yl = a.get_ylim()[1]
a.axvline(Bd, color=RED, lw=2.4, ls="--"); a.text(Bd, yl * 0.97, " budget 0.1 Gy", color=RED, fontsize=11.5, va="top", fontweight="bold")
a.axvline(qv, color=ORANGE, lw=3); a.text(qv, yl * 0.80, " 97th pct", color=ORANGE, fontsize=11.5, va="top", ha="left", fontweight="bold")
a.set_xlabel("used + next step + way out (Gy), 32 samples", fontsize=11.5); a.set_yticks([])
a.spines["left"].set_visible(False)
a.text(0.70, 0.42, "over budget\n→ WITHDRAW", transform=a.transAxes, ha="right", fontsize=13.5, fontweight="bold", color=RED)
fig.text(0.665, 0.97, "③ Check: keep enough dose to get home", fontsize=15, fontweight="bold", color=ORANGE, va="top")
fig.savefig("docs/figures/alg_overview.png", bbox_inches="tight", pad_inches=0.1)
plt.close(fig)
