# Design decisions (with the evaluation behind each)

Every non-obvious choice is listed with the alternatives considered, how
they were compared, and the result. Numbers come from scripts in `scripts/`
(raw outputs in `docs/results/`) run on a 4-core CPU container; rerun them on
the cluster for the paper.

---

## D1 — Build MAPPO / MAPPO-L in-house instead of using a MARL library

| Option | Verdict |
|---|---|
| MARLlib | pinned to Ray 1.8 / Python ≤ 3.8; no per-agent constraints |
| on-policy (MAPPO reference repo) | not pip-installable, no cost critic |
| PKU Safe-Policy-Optimization (MAPPO-L) | single shared λ, no retirement masking, tied to Safety-Gymnasium |
| BenchMARL / TorchRL | no Lagrangian, heavy dependency for a 5-action grid task |
| **Own ~450-line implementation** | ✔ per-robot λ, cost critic, retirement mask, shield-masked log-probs |

Risk of bugs in own code is handled by unit tests (`tests/test_algos.py`: λ rule
equal to the Safe-Policy-Optimization update, resume, all four variants train
and evaluate) and by the learning curves in D18.

## D2 — Wall attenuation: exact slab clipping, Numba-fused

FR-PHY-05 needs the path length through obstacles for every (particle, robot)
pair — up to 16 envs × 2000 particles × 6 robots × 7 boxes per step.

| Method (B=16, P=2000, N=4, K=7) | time / call | mean abs. error |
|---|---|---|
| ray sampling, 20 pts | 1557 ms | 0.028 m |
| ray sampling, 50 pts | 5272 ms | 0.011 m |
| **exact slab (Liang–Barsky), NumPy** | 380 ms | 0 |
| exact slab, torch float32, 4 threads | 62 ms | 2.5e-3 (float32) |
| **exact slab, Numba fused loop** | **3.8 ms** | 0 (≤ 1e-13 vs NumPy) |

Exact clipping is possible because obstacles are rectangles, so per-cell
traversal (Amanatides–Woo) gains nothing. The NumPy version stays as the test
oracle and fallback. Rays are treated in 3-D (source on the floor, detector
0.3 m up): the chord through a vertical-walled block is scaled by d₃/d₂.

## D3 — Particle-filter variant: adaptive tempering (3 stages)

TBq sources give 10³–10⁶ counts per reading, so the Poisson likelihood is
extremely sharp. `scripts/eval_estimator.py`, 48 episodes, 4 random-walk robots,
100 steps, 2000 particles, Cs-137, no model error:

| Variant | empty room: success / 95 % calibration | 5 obstacles: success / calibration | ms / env-step |
|---|---|---|---|
| SIR (resample, no jitter) | 15 % / 0 % — collapses (σ ≈ 3e-5 m) | 38 % / 2 % | 1.7 |
| Regularised PF (Silverman jitter) | 92 % / 79 % | 67 % / 58 % | 1.6 |
| **Tempered, 3 stages** | **100 % / 100 %** | **92 % / 83 %** | 4.2–4.8 |
| Tempered, 6 stages | 100 % / 98 % | 92 % / 88 % | 6.7–7.7 |

The tempered filter splits each update into likelihood powers chosen by
bisection so ESS ≥ P/2, with resample + jitter between stages (progressive
correction). 6 stages cost 60 % more for no clear gain → **3 stages default**
(`pf_max_stages`, raise for final evaluation if wanted). Profiling showed all
stages are used every step, so the cost is inherent; it was cut 3.5× by fusing
geometry, attenuation, expected counts and log-likelihood into one Numba kernel.
The PF state is (x, y, log₁₀ A): activity is log-uniform, so the log scale
matches the prior. Calibration (truth inside the 95 % ellipse) is reported
because an over-confident PF ends episodes early with a wrong answer.

## D4 — Room generation

* Obstacles may not overlap (overlap would double-count attenuation) and must
  keep the free space 4-connected (`scipy.ndimage.label`), so every source is
  reachable and BFS navigation never fails.
* Robots enter through a **door** on a random wall and start on the free cells
  nearest to it (`start_mode="random"` available). This matches deployment and
  gives the perimeter baseline a meaningful start. Sources are ≥ 5 m from every
  start.
* Robots may share a cell (no inter-robot collisions in semester 1).

## D5 — One batched core with per-slot RNGs

Options: (a) Python loop over single-env objects, (b) subprocess vector env,
(c) **one core holding (B, …) arrays**. The PF dominates cost and is much faster
batched (D2), so (c). Each slot re-creates its generators from the episode seed
at reset (separate streams for layout, source, budgets, PF, measurements), so
episode *s* is bit-identical alone or inside any batch
(`test_batch_independent_of_composition`) — required for a fixed test set.

Throughput after profiling-driven fixes (C connectivity check, vectorised
run-lengths, cached PF moments): **~210 env-steps/s (840 agent-steps/s) on 4
cores**, flat for B = 8–32; 2 M env steps ≈ 2.6 h → NFR-03 (< 12 h) is met
with margin. With two concurrent runs per 4 cores this drops to ~90 each.

## D6 — Measurement noise: correlated model-error field (most important finding)

**Problem found in calibration.** With the PRD's pure Poisson model, a TBq
source is localised from the doorway: every episode ended after 6–9 steps,
robots never approached, dose stayed < 1 % of budget, violation = 0 % for every
budget / isotope / policy (`docs/results/calibration_v1.json`). There was **no
dose-versus-information trade-off**, so RQ1–RQ3 would be vacuous whatever the
budget. Calibrating budgets (AC-3) cannot fix this.

**Cause.** Relative Poisson noise at 10⁵ counts is 0.3 %, far below the
real-world error of an analytic inverse-square model (scatter, build-up,
detector calibration, geometry: typically 10–30 %).

**Fix evaluated** (`scripts/compare_noise_models.py`, Cs-137, 48 episodes):
multiplicative error λ·exp(σz − σ²/2), with z either i.i.d. per reading or a
smooth Gaussian random field fixed per episode (scatter is geometry-dependent,
so re-measuring at the same spot does not average it out). The PF uses the
matching log-normal–Poisson likelihood `log(k+½) ~ N(log(λ+½), σ² + 1/(λ+½))`.

| Noise model | perimeter (far) success | approach (near) success | approach dose / budget | trade-off? |
|---|---|---|---|---|
| none (PRD) | 62 % | 65 % | 0.1 % | no |
| i.i.d., σ = 0.2 | **92 %** | 90 % | 12 % | no — averaging removes it |
| field, σ = 0.2 | 81 % | 94 % | 12 % | yes |
| **field, σ = 0.3, ℓ = 3 m** | 81 % | **96 %** | 21 % | **yes, clearest** |

Only the correlated field makes close measurements genuinely more valuable:
with a fixed relative error, positional information grows like 1/r², the same
rate as the dose. **Default: `model_error: field`, σ = 0.3, ℓ = 3 m.** This
extends FR-PHY-03 and must be stated in the paper; the literature value for σ is
an open item. `model_error: none` reproduces the PRD model exactly.

## D7 — Calibration of isotope and budget (AC-3, provisional)

For a dose-unaware policy the dose does not depend on the budget, so one run
with an infinite budget gives the whole violation-vs-budget curve
(`scripts/calibrate.py`, 96 episodes, field σ = 0.3):

| Policy / isotope | violation at 0.05 / 0.1 / 0.2 / 0.3 / 0.5 / 1 / 2 Gy |
|---|---|
| approach, Cs-137 | 43 / 30 / 24 / 18 / 14 / 6 / 5 % |
| approach, Co-60 | 69 / 51 / 40 / **30** / 25 / 18 / 9 % |
| greedy (β = 0), Co-60 | 28 / 16 / 7 / 4 / 1 / 0 / 0 % |

Dose is heavy-tailed (Co-60 approach: median max dose 0.11 Gy, p90 1.9 Gy)
because activity is log-uniform over two decades: safe behaviour requires
inferring the activity — good for the research question. Chosen: **Co-60**
(matches the motivating Hueypoxtla 2013 incident) at **0.3 Gy**. The sanity
runs (D18) showed learned MAPPO violating only ~3–6 % at 0.3 Gy, so per the
PRD rule the budget is being lowered: **0.1 Gy is the current candidate**,
pending the week-5 MAPPO check (`scripts/calibrate.py --policies checkpoint:...`).

## D8 — Episode termination: team declares when confident

Options: fixed 200-step horizon vs **terminate when the PF position σ (largest
eigenvalue of the x-y covariance) < 0.3 m** (after ≥ 5 steps), or when all robots
are retired, or at 200 steps. A fixed horizon keeps robots in the field after
localisation and charges dose for nothing; the declaration rule uses only
deployable information and gives "time to localise" a meaning. Success is still
judged against the truth (FR-OBS-05), so an over-confident declaration counts
as a failure. Switch: `terminate_on_confident`.

## D9 — Fixed robot↔budget assignment for per-robot λ

If budgets were shuffled across robot slots every episode, "the multiplier of
robot 2" would mix all budget levels and could not target the binding robot.
**Default `shuffle_budgets: false`**: robot *i* always has budget *bᵢ*; the
robot ID and its budget are both in the observation. Shuffled budgets remain
available for generalisation tests. Unequal ratios are normalised to keep the
mean (team) budget equal to the equal-budget setting, so RQ3 compares teams
with the same total budget.

## D10 — Retirement and cost semantics

* Dose is tracked until retirement; a retired robot is considered lost, so it
  accrues no further dose (otherwise "max dose" would keep growing for an
  already-failed robot). The step on which the budget is crossed is recorded.
* For the learner, retirement is that robot's terminal state (GAE stops; later
  steps are masked, FR-BUD-04).
* Version B's indicator cost is placed on the **crossing step**, not at episode
  end: after retirement the robot's steps are masked, so an end-of-episode cost
  would never reach its cost critic. Undiscounted sums are identical.
* Costs are divided by the robot's budget, so version A's limit is a fraction
  (0.75) and one λ scale fits robots with different budgets.

## D11 — Greedy information measure

Var[log λ] over particles ignores Poisson noise and over-values far cells.
Used: Gaussian mutual-information approximation ½·log(1 + Var[λ]/E[λ]) at the
same cost; `info="logvar"` kept for comparison. Robots choose sequentially with
a penalty for picking a cell a teammate already chose.

## D12 — Shield

Uses only the posterior (128 particles): blocks an action if
`dose + h · q₀.₉₅(step dose at the new cell) ≥ budget`, with h = 3 steps of
reserve to back off. Never returns an empty mask (falls back to the least
dangerous action). For MAPPO-L + shield the mask is applied to the logits during
training too, so stored log-probabilities match the executed policy.

## D13 — Observation additions beyond FR-OBS-01

* Own dose rate from the robot's dosimeter (standard equipment; directly
  informs the constraint) — switch `obs_dose_rate`.
* Time left (makes time-limit truncation Markov, see D17).
* Free run-length to the next obstacle in each direction (in addition to
  blocked flags).
* Teammates sorted by distance and padded to `max_agents` (permutation
  invariant; allows evaluating with more robots, E5).
* `obs_budget: false` removes own and teammates' budget / remaining budget
  (E4 ablation).

## D14 — Air attenuation in the dose model

FR-PHY-01 lists only walls. Over 20 m, air removes ~13 % (Co-60) to 17 %
(Cs-137) of the dose, and the detector model already includes it, so it is
included for consistency (`dose_air_attenuation: true`; set false for the
literal PRD model).

## D15 — Detector height instead of a distance clamp

A 1/r² model diverges when a robot is on the source cell. Instead of an
arbitrary r_min, the detector/electronics sit 0.3 m above the floor-plane
source, which is physical and smooth.

## D16 — Lagrange multiplier update

Default: projected gradient ascent `λ ← clip(λ + 0.05·(Ĵc − d), 0, 100)` once
per rollout from the mean episode cost of finished episodes — the
Safe-Policy-Optimization rule (FR-ALG-06). PID Lagrangian (Stooke et al. 2020)
is available (`algo=mappo_lag_a_pid`) for the "λ oscillates" risk. Policy
advantage: `(Â_r − λᵢ Â_cᵢ)/(1 + λᵢ)` with reward and cost advantages
standardised separately.

## D17 — Time-limit truncation treated as terminal

Time-left is in every observation and in the critic state, so the problem is
Markov and bootstrapping past the limit is unnecessary.

## D18 — Sanity training results (this container, 1 seed — not paper results)

Main setting at **0.1 Gy**, same 200 test episodes for every method
(`docs/results/sanity01/`; curves in `learning_curves.png`). MAPPO ran 300 k
env steps, MAPPO-L (B) 150 k (λ lr = 1.0, per-robot limit 0.05).

| method | success [Wilson 95%] | violation [Wilson 95%] | median error (m) | max dose/budget | steps |
|---|---|---|---|---|---|
| random | 0.44 [0.37, 0.51] | 0.065 [0.038, 0.108] | 1.26 | 0.18 | 85 |
| perimeter | 0.83 [0.78, 0.88] | 0.075 [0.046, 0.120] | 0.32 | 0.27 | 20 |
| approach | 0.92 [0.87, 0.95] | 0.470 [0.402, 0.539] | 0.28 | 0.95 | 28 |
| greedy (β = 1) | 0.88 [0.82, 0.91] | 0.100 [0.066, 0.149] | 0.29 | 0.30 | 16 |
| shielded greedy | 0.81 [0.75, 0.86] | 0.020 [0.008, 0.050] | 0.31 | 0.19 | 16 |
| MAPPO | 0.85 [0.79, 0.89] | 0.090 [0.058, 0.138] | 0.32 | 0.35 | 27 |
| MAPPO-L (B) | 0.76 [0.70, 0.81] | 0.070 [0.042, 0.114] | 0.46 | 0.24 | 29 |

Readings:
* The pipeline learns: MAPPO success 0.46 → 0.85, episode length 80 → 25 steps.
* **AC-4 not yet shown**: MAPPO beats random clearly but only ties perimeter on
  success (CIs overlap) and is slower (27 vs 20 steps). Needs the full 2 M-step
  budget and 10 seeds.
* **AC-3 not met at 0.1 Gy**: unconstrained MAPPO violates 9–12 %, not ≥ 30 %.
  Learned search is efficient and ends early, so it rarely needs to sit near
  the source. Next calibration candidates: 0.05 Gy, or longer `confident_sigma`
  requirements; decide with the advisor whether AC-3's 30 % is the right bar.
* **Version A** at 0.75 never activated λ in the 0.3 Gy run: the expected dose
  fraction (~0.1) is dominated by low-activity episodes, while violations come
  from the heavy high-activity tail. An expectation constraint cannot control a
  tail probability — version B is the formulation that matches RQ1.
* The shielded greedy baseline is the one to beat on safety (2 % violation at
  81 % success).

## D19 — Version B limit split across robots (union bound)

In the run above λ stayed ≈ 0.02: each robot's own violation rate (~2.5 %) was
below its 0.05 limit, while P(*any* robot violates) was ~7–10 %. RQ1's target
("every robot within budget in ≥ 95 % of episodes") is a **team** chance
constraint; per-robot limits of d allow up to N·d at team level. Since
P(∪ᵢ violateᵢ) ≤ Σᵢ P(violateᵢ), per-robot limits **d/N** guarantee the team
target. Default now `team_chance_split: true` (0.05/4 = 0.0125 for 4 robots);
the λ learning rate for version B must also match the indicator cost's scale
(lr ≈ 1.0, not 0.05). Both changes still need a training run to confirm.

## D20 — 3-D simulation: MuJoCo for motion, one shared radiation model

**Options compared** (for robotics credibility and the semester-2 path):

| Simulator | Robotics relevance | Usable here | Verdict |
|---|---|---|---|
| ROS 2 + Gazebo Harmonic | industry standard; real-robot route | no (ROS package servers blocked) | exporter now, bridge on a local machine (`docs/ROS2_GAZEBO.md`) |
| NVIDIA Isaac Sim / Lab | GPU-scale RL | no GPU | optional later |
| **MuJoCo 3.17** | standard in robot learning | yes (pip wheel, OSMesa rendering) | **built** |
| PyBullet | declining maintenance | source build only | rejected |

**Integration choice.** (a) A second, separate 3-D simulator would duplicate
the radiation physics and drift from the training model. (b) **MuJoCo
simulates only robot motion** (slide-joint bases with velocity motors,
contacts with walls, obstacles and each other); dose, counts and the particle
filter come from `RadSearchCore.step(..., xy_override=positions)`. Chosen:
(b). The detector sits on a mast at 0.3 m, the same height the physics uses.

**Checks** (`tests/test_sim3d.py`): MuJoCo's ray cast and our slab clipping
agree on blocked paths for > 200 random pairs; robots reach the next cell in
one step at 0.5 m/s; robots collide instead of overlapping; with perfect
tracking a 3-D mission reproduces the 2-D doses; exported Gazebo worlds are
valid SDF 1.9 with every obstacle.

**Sim-to-sim transfer** (`scripts/eval_3d_transfer.py`, MAPPO sanity model,
0.1 Gy, the same 30 test missions; `docs/results/sim3d_transfer.json`):

| Robot motion | success | some robot over budget | steps | mean tracking error |
|---|---|---|---|---|
| grid (2-D) | 93 % | 10 % | 17.8 | 0 |
| MuJoCo, 0.5 m/s | 93 % | 10 % | 17.8 | 0.07 m |
| MuJoCo, 0.15 m/s | 90 % | 10 % | 17.4 | 0.09 m |
| MuJoCo, 0.08 m/s | 83 % | 10 % | 26.0 | 0.53 m |

The grid-trained policy transfers as long as the robot can keep pace with
its 10-s decisions. Below that, success drops and missions take ~45 % longer.
A fix to try: randomise motion speed and tracking error during training
(domain randomisation). 30 missions per row: indications only.

**Known issue.** With `MUJOCO_GL=osmesa` set, `torch.optim.Adam` segfaults
(native-library clash, independent of import order). Only the rendering
script sets it, and only on headless Linux.

## D21 — Safe exit, predicted-dose observation, strong sources, 0.1 Gy

**Problem.** In the sanity runs ~4 in 10 robots that approached a strong
source were stranded next to it: the mission ended when the source was found,
so a robot that spent its whole budget on the last step cost the team
nothing. Robots also approached equally close whatever the source strength.

**Decision (agreed with the author: option b).** A robot is only safe if it
can still get out. When a mission ends, every robot still in the field drives
back to the door; that exit dose is added to its dose, and a robot that would
exceed its budget is **stranded** and counts as a violation (cost A gets the
exit dose, cost B the indicator at the final step). `egress_required: false`
restores the old rule.

**Exit-route computation — options compared.** (a) Dijkstra on dose (the
lowest-dose route of any length) per environment per step: exact but a
Python heap loop every step. (b) **Shortest route to the door, picking the
lowest-dose one among equally short routes**, computed level by level with
vectorised array operations over the whole batch. Chosen: (b). In a
20 × 20 m room detours rarely pay, and (b) adds little cost to a step.

**New observation** (`obs_predicted_dose`, +6 features): the predicted step
dose for each of the 5 moves and the estimated exit dose, both divided by
the remaining budget. They are computed from the team's *estimate* (posterior
mean), never the true source, so a real robot could compute them. Old
checkpoints keep their layout (`LearnedPolicy.with_pred`).

**Strong sources and budget.** Main setting now 10–100 TBq (all violations
came from ≥ 10 TBq; the cited incidents are 15.7–111 TBq). AC-3 re-check
with the old MAPPO model under the new rules, 100 missions
(`docs/results/ac3_egress_strong_sources.json`):

| Policy | budget | success | some robot over budget | stranded |
|---|---|---|---|---|
| MAPPO (old model) | 0.1 Gy | 84 % | **30 %** | 11 % |
| MAPPO (old model) | 0.2 Gy | 85 % | 15 % | 3 % |
| MAPPO (old model) | 0.3 Gy | 87 % | 10 % | 1 % |
| greedy, no dose term | 0.1 Gy | 86 % | 35 % | 12 % |

**0.1 Gy** is the only level meeting AC-3 (≥ 30 %); it is below the PRD's
0.2–2 Gy range, which must be flagged to the advisor. Re-check with a model
trained under the new rules.

Tests: `tests/test_egress.py` (exit cost along shortest/lowest-dose route,
stranding, switch-off, estimate = truth when the estimate is exact,
observation layout, old checkpoints still run).
