# Mathematical formulation: six questions to settle before the main experiments

*16 November 2026. For each question: what the code does today (with file references), what is missing or simplified, and the decision or experiment that settles it. Notation: robots i = 1..N, time steps t = 1..T (Δt = 10 s, T ≤ 200), source θ = (s, A) with position s ∈ ℝ² and activity A, robot position xᵢ(t), budget Bᵢ.*

---

## Q1. Radiation model: how realistic is the activity–distance–shielding–counts relation?

### Today (`radsearch/physics.py`, `physics_constants.yaml`)

Distance with detector height h = 0.3 m: d(x, s) = √(‖x − s‖² + h²).

**Dose rate at the robot** (Gy/h):

```
Ḋ(x; θ) = Γ · A / d² · exp(−μ_air d) · exp(−Σ_k μ_k ℓ_k(x, s))
```

with Γ = 3.51·10⁻⁴ Gy·m²/(GBq·h) for Co-60, μ_air = 6.85·10⁻³ m⁻¹, μ_k the linear attenuation of obstacle k (concrete 13.4 m⁻¹), ℓ_k the chord length of the straight line source→robot through obstacle k. Step dose: ΔD = Ḋ · Δt.

**Expected counts in one dwell** (t_dwell = 10 s):

```
λ(x; θ) = [ A · n_γ · ε · Ω(d) · exp(−μ_air d) · exp(−Σ_k μ_k ℓ_k) + b ] · t_dwell,
Ω(d) = ½ (1 − d / √(r² + m d + d²))
```

with n_γ = 2 photons per decay, intrinsic efficiency ε = 0.01, detector radius r = 5 mm, background b = 1 cps.

**True measurement:** k ~ Poisson(λ · exp(σ z(x) − σ²/2)), where z is a standard Gaussian random field with correlation length 3 m and σ = 0.3 (mean-preserving, spatially correlated model error).

### Simplifications and one real gap

| Item | Status | Effect |
|---|---|---|
| Point source, straight-line (narrow-beam) attenuation | modelled | standard for search papers |
| **Build-up / scattered photons** | **not modelled** | behind shielding the real dose is higher than exp(−μℓ) predicts (build-up factor > 1); the model is optimistic exactly where robots hide |
| Detector dead time / saturation | off (dead time = 0); efficiency tuned to keep counts < 10⁷ per dwell | real probes saturate near TBq sources |
| Detector energy and angular response, robot self-shielding | not modelled | second-order |
| Dose in silicon vs air kerma | taken as equal | same order for 1.25 MeV photons |
| **Model error only in the counts, not in the dose** | **gap** | the simulator's true dose uses exactly the physics the filter uses. Given the correct (s, A), dose prediction is exact; all safety error comes from not knowing (s, A). In reality, wrong attenuation or missing build-up makes both counts and dose wrong, in a correlated way. **Today's safety results are therefore optimistic.** |

### Decision needed
1. **Add dose-model error correlated with the count error.** For example, true dose = Ḋ · exp(σ_D z_D(x) − σ_D²/2), with z_D correlated with z. Then the safety layer faces the same kind of model mismatch that real robots face.
2. **Build-up factor:** add a simple build-up B(μℓ) ≈ 1 + a μℓ (or a Berger form) to the true dose only, as a further source of mismatch. Decide whether to include it in the filter's model.
3. **Dead time:** turn on a non-paralysable dead-time model (k_obs = k / (1 + k τ / t)) as a stress test.

Experiment: re-run the reference rule (greedy + reserve, q = 0.97) with 1 and 2. If violations jump far above 4.3%, the current safety layer is relying on an exact dose model, and Q2 and Q4 become more urgent.

---

## Q2. Belief model: is the posterior over location and activity calibrated?

### Today (`radsearch/estimator.py`, `physics.measurement_loglik`)

State θ = (s_x, s_y, log₁₀ A). Prior: uniform over free cells × uniform in log₁₀ A **over the same 10–100 TBq range the simulator samples from** (the filter is told the true range).

Likelihood of one reading, assumed **independent** across readings and robots:

```
log(k + 0.5) ~ N( log(λ_θ + 0.5),  σ_m² + 1/(λ_θ + 0.5) ),   σ_m = 0.3
p(k_{1:t} | θ) = Π_j p(k_j | θ)
```

2,000 particles, tempered resampling.

**The mismatch:** in the simulator the model errors of nearby readings are correlated (shared field z). The filter treats them as independent, so n readings count as n independent pieces of evidence when the effective number is n_eff < n. The posterior is too narrow.

### Definition of calibration

For a credible region R_α of the posterior at level α:

```
C(α) = P( θ* ∈ R_α ),   calibrated  ⇔  C(α) = α  for all α
```

Measured on 300 missions: C(0.9) ≈ 0.52–0.65 for position (D24). **Overconfident.**

**What safety actually needs** is calibration of the *predicted dose*, not of the position. Let F̂ be the predictive CDF of the next-step + exit dose for the chosen move, and q̂₀.₉₇ its 97th percentile. The safety layer is calibrated if

```
P( D_true > q̂₀.₉₇ ) = 0.03,  equivalently  u = F̂(D_true) ~ Uniform(0, 1)
```

**This test has not been run yet.** It is the single most informative experiment for the thesis.

### Options if it fails
- Tempered likelihood: p(k_j | θ)^{1/κ}, with κ ≈ n / n_eff estimated from the field correlation length.
- Larger σ_m. Already tried: this alone shifts the trade-off but does not improve it (D24).
- Explicit discrepancy: model z as a latent Gaussian process in the likelihood (Brynjarsdóttir & O'Hagan).
- Conformal calibration of the dose quantile online, from residuals between predicted and measured counts.
- A wider activity prior than the simulator's range, so the filter does not get the range for free.

---

## Q3. Safety definition: hard limit or chance constraint?

### Today
Each robot has a hard physical limit Bᵢ = 0.1 Gy. The mission requirement is **probabilistic**: at most 5% of missions may have any violation. A violation is either (a) dose in the field reaching Bᵢ, or (b) a robot that cannot get out because dose so far + true exit dose ≥ Bᵢ ("stranded").

### Precise statement (proposed)

Let Dᵢ be robot i's field dose at the moment it leaves (withdraw or mission end), and Eᵢ the true dose of its exit route. Then:

```
Budget (physical, per robot):     Bᵢ
Mission chance constraint:        P( max_i (Dᵢ + Eᵢ) / Bᵢ > 1 ) ≤ δ,   δ = 0.05
```

This is **not** an almost-sure constraint. With an unknown source no policy can guarantee zero violations without being extremely conservative. It is also **not** the expected-cost constraint of MAPPO-Lagrangian (E[Σ cost] ≤ d), which does not imply the chance constraint.

### From mission-level δ to the per-step rule
The safety layer applies a per-step test at quantile q. A union bound over N robots and T steps gives δ ≤ N · T · (1 − q). For δ = 0.05, N = 4, T = 200, that would require 1 − q ≈ 6·10⁻⁵, which is far too conservative. In practice only the few steps near a robot's limit carry risk, so the effective number of risky steps is small. Empirically q = 0.97 gives 4.3%.

**Decision needed:** state the requirement as the mission chance constraint above. Report the per-step quantile as a tuning parameter calibrated against δ. Optionally use risk allocation (Ono & Williams) to set a different quantile per step or per robot.

Also report: the uncertainty interval of the violation rate (needs about 3,000 missions to separate 4% from 5%), per-robot tail dose (CVaR), and stranded vs in-field violations separately.

---

## Q4. Exit reserve: how is the exit route and its uncertain cost computed?

### Today (`env.exit_costs`, `shield.predictive_fields`, `ReserveWithdraw`)

Grid of 1 m cells; the door is cell c₀. Let dist(c) be the breadth-first-search (BFS) distance to the door. The exit cost from cell c is the minimum dose along **shortest** routes:

```
E(c; θ) = min over shortest grid paths c → c₀ of  Σ_{c' on path, c' ≠ c₀}  ΔD(c'; θ)
```

computed by dynamic programming, one BFS level at a time. Each cell entered costs one step dose (the robot moves one cell per 10 s).

**True exit:** at withdraw, the robot is charged E(c; θ*) at once and leaves.

**Predicted exit:** draw J = 32 particles θ_j from the posterior and compute, for each candidate next cell c′, the total S_j(c′) = ΔD(c′; θ_j) + E(c′; θ_j). The rule allows the move if

```
Dᵢ + Quantile_{0.97}{ S_j(c′) : j = 1..32 } ≤ Bᵢ
```

The quantile is taken over the **sum** (next step + exit) per particle, not the sum of two quantiles, so correlations between the two are kept. Withdraw is always allowed.

### Points to state or fix
1. **With 32 samples, the 97th percentile is essentially the maximum** (the 31st of 32 order statistics). This gives a clean interpretation: if the posterior were calibrated, P(true value > max of n i.i.d. posterior samples) = 1/(n + 1) = 1/33 ≈ 3%. So "q = 0.97 with 32 samples" ≈ "plan for the worst of 32 plausible sources". The 97% level only holds if the posterior is calibrated, which links Q4 back to Q2.
2. **Shortest routes only.** A longer route through a radiation shadow could cost less dose. Using lowest-dose routes (Dijkstra on dose instead of BFS distance) would be cheap and more realistic.
3. **Instant exit.** No time passes and no measurements are taken on the way out; the robot is not an obstacle to others while leaving. This is conservative for the estimate and optimistic for congestion at the door.
4. **No model error in the exit dose** (see Q1).
5. **Joint feasibility:** each robot's mask is checked alone. Two robots that both need the same doorway at the same moment are not considered.

---

## Q5. Risk allocation: how should robots with different remaining budgets share the work?

### Formal setting
Remaining safe budget of robot i at time t:

```
bᵢ(t) = Bᵢ − Dᵢ(t) − Ê_q,ᵢ(t)      (dose left after reserving the predicted exit)
```

A candidate measurement location x has expected information gain I(x | belief) (expected entropy reduction of the posterior) and predicted dose cost c(x) plus a change in exit cost.

A one-step team allocation:

```
max over assignments (x₁..x_N)  Σᵢ I(xᵢ | belief, other robots' readings)
s.t.  P( Dᵢ + cᵢ(xᵢ) + Eᵢ(xᵢ) > Bᵢ ) ≤ εᵢ   for each robot,   Σᵢ εᵢ ≤ δ_step
```

Two levers:
- **Who goes where:** high-information, high-dose locations should go to robots with large bᵢ.
- **How risk is split (εᵢ):** equal split vs adaptive allocation.

### Testable hypotheses
- **H1:** in teams with unequal budgets, a robot's share of team dose and of close-range readings increases with its budget share. Measure the slope of dose share against budget share. The Spearman correlation from the proposal is too coarse.
- **H2:** learned (MAPPO) allocation beats both fixed roles (Huo-style: low-budget robots stay at the edge) and budget-agnostic greedy, at the same δ.
- **H3:** robots withdraw in order of remaining budget, and the team stays informative after withdrawals. Report the spread of exit times.

Status: unequal budgets are already supported in the code (`budget_ratio`, remaining budget in each robot's observation). The experiment comes after the P1 pilot.

---

## Q6. Learning necessity: does MAPPO have a decision structure to learn that greedy cannot?

### What greedy does
One step of lookahead: choose the move that maximises information gain minus a dose term, then apply the safety mask. It cannot represent:

1. **Option value of budget.** Spending dose early on low-value readings removes the ability to take a decisive close reading later.
2. **Coordination.** One scout goes close while others stay back, and robots avoid duplicate readings. The v2 MAPPO policy already learned a single scout (about 1 robot approached vs about 3 for "everyone approaches").
3. **Stopping and withdrawal timing.** "One more reading or leave now" is an optimal-stopping problem.
4. **Exit-aware positioning.** Measuring from cells whose exit route is cheap, for example behind a shadow, keeps more budget for later.

### How to tell whether these matter: the headroom test
Define success at fixed safety (δ = 5%) for:
- the reference rule (greedy + reserve);
- a **tuned** greedy (grid search over its dose weight and quantile);
- a **non-myopic planner** (Monte-Carlo tree search with k-step lookahead on the belief);
- a **clairvoyant** upper bound (true dose known, same estimator).

```
Headroom H = success(non-myopic or clairvoyant) − success(tuned greedy)   at the same violation rate
```

- **H < about 5 points:** this setting does not need learning. Move the learning study to harder settings (tighter budgets, more obstacles, unequal budgets, more robots), where coordination should matter more.
- **H large:** learning has room. MAPPO should approach the planner's success at a fraction of its compute per decision.

This also frames the P1 pilot result honestly. If MAPPO + reserve matches but does not beat the rule, the headroom test tells us whether that is a limit of the method or of the setting.

---

## Summary: what to do, in order

| # | Action | Kind | Cost |
|---|---|---|---|
| 1 | Q2: dose-calibration test, P(D_true > q̂₀.₉₇) vs 3% | experiment | about 1 h here |
| 2 | Q1: add correlated dose-model error (and build-up) to the true dose; re-run the reference rule | code + experiment | half a day |
| 3 | Q3: write the chance constraint as the official safety definition; report stranded vs in-field, per-robot tail dose | writing + metrics | small |
| 4 | Q4: lowest-dose exit routes (Dijkstra) and joint door feasibility check | code | small |
| 5 | Q6: tuned greedy + clairvoyant bound (+ MCTS later) → headroom | experiment | 1–2 days |
| 6 | Q5: unequal-budget experiments with H1–H3 metrics | experiment | after P1 |
