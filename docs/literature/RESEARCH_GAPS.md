# Research gaps and ideas from the authors' own words

*10 November 2026. Eight readers went through all 234 papers and recorded what each paper says about its limitations, assumptions, open problems and future work, with exact quotes (checked against the source text). Per-paper records: `gaps/gaps_*.json`.*

**Evidence:**
- **Material read:** 90 papers in full text, 113 from the abstract only, 31 from my earlier summary only (see `FULLTEXT_COVERAGE.md`).
- **What was found:** 674 gap statements. 263 are limitations, 89 open problems, 87 future work, 86 assumptions. The other 149 are inferred by the readers and marked as such.
- **Coverage:** 182 papers state at least one gap themselves.
- **Caveat:** for abstract-only papers, future-work sections were not seen, so gaps there are undercounted.

## The picture in one paragraph

Every cluster names the same missing piece from its own side:
- **Radiation search:** robots approach the source with no dose limit.
- **Nuclear robotics:** dose is minimised against a known field.
- **Budgeted exploration:** budgets are deterministic, and return guarantees exist only for single robots or for rechargeable batteries.
- **Hazard-aware search:** robot loss is binary or random.
- **Safe RL:** constraints hold only in expectation, and the safe set is assumed to be given.

A second, independent theme appears in four clusters: **estimates become overconfident when correlated model error is ignored, and safety rules built on them inherit the error.** The thesis has measured exactly this, which turns it from a side finding into a possible method contribution.

## Ranked ideas

Status: **Core** = the thesis already does it; **Easy** = small code change or extra experiment; **Moderate** = new component; **Future** = out of scope, list as future work.

### 1. Hard, estimate-based dose budget with an exit reserve. Core, confirmed in every cluster

| Cluster | What the papers say |
|---|---|
| A, radiation search | P001: approaching the source "is potentially unsafe" and "increases the chance of radiation damage to robots", with low-risk paths "intended to be planned by the user". P004: "Robots destined for nuclear environments currently do not practice ALARP." P032 assumes "it is harmless to expose the robot". |
| B, multi-robot radiation search | P060 assumes intensities "not hazardous for the electronics". P047: exposure is motivation only. P038 tracks time and accuracy only. P041 assumes a known field. |
| C, nuclear robotics | P101: high doses limit "the platform's operational time". P086: "the highly uncertain radiation field ... pose[s] significant challenges for traditional path planning". |
| E, budgeted exploration | P188: "Future work includes the consideration of multi-robot systems." P201: "may require consideration of the probability of robots running out of charge". P177: "none of these approaches guarantee 'homing'". |
| F, hazard-aware search | P210: "robots always survive events"; P211 injects failures at random. |
| D, safe RL | P156 lists sample-path constraints as future work. P158: "we do not have a 'real' concept of budget". |

**Use:** this is the related-work argument for the main contribution. Several authors list a piece of it as future work.

### 2. Calibration-aware safety layer under model discrepancy. Easy to Moderate; strongest new idea

- **Problem stated by the authors:**
  - P008: "when the true obstacles attenuate more than the particle filter assumes, the particle filter posits that the sources must simply be weaker"; more study "warrants additional research".
  - P206: ignoring model discrepancy "may lead to biased and over-confident parameter estimates".
  - P222: "biased, overconfident prediction".
  - P195: correlations must be "considered to avoid overconfidence".
  - P203 treats risks per cell as "independent of the others".
  - P208 assumes "conditional independence between robot observations".
  - P133: "the contingency of all guarantees upon the validity of the model".
  - P155: "account for state estimation errors ... in safe learning control" is an open challenge.
  - P096: confidence "is heavily linked to the length scale".
  - Particle loss: P024, P027, P219.
- **Idea:** make the dose safety layer aware of its own miscalibration. Options, cheapest first:
  - inflate the predicted dose spread by an error term for correlated attenuation and bias;
  - adapt the quantile online from residuals between predicted and measured counts;
  - put a spatially correlated discrepancy term (Gaussian process) into the likelihood;
  - estimate activity analytically (Rao-Blackwellised gamma–Poisson) to reduce particle degeneracy (P218, P219).
- **Why it matters:** the thesis already shows that the mean-based rule fails (14.7%) and that calibrating the filter alone just slides along the safety–success curve. A safety layer that corrects for discrepancy is a concrete way to try to move the curve, without learning.
- **Experiment:** count how often the true next-step plus exit dose exceeds the 97th-percentile prediction (it should be at most 3%), then re-run the D24 sweep with each fix.

### 3. CVaR instead of the 97th percentile. Easy ablation
- P135: the percentile (VaR) "does not quantify the costs that might be suffered beyond its value in the α-tail".
- P149: CVaR is the "expected cost under worst-case modeling errors".
- P193: the expectation "is a risk-neutral measure and may not be desirable".
- P203 notes that estimating high quantiles needs care (importance sampling).
- **Experiment:** swap the mask's percentile for CVaR over the particles at matched levels and compare on the trade-off plot. Also check stability with 32 vs 128 particles.

### 4. Constrained learning that is not timid. Easy
- P146: under large penalties the agent "will only focus on constraint satisfaction and ignore the underlying reward signal".
- P157: "sensitive to the initialization of the Lagrange multipliers and the learning rate".
- P122: the integral "easily gets overly large, leading to policy over-conservatism".
- P156: "too much penalty could prevent the agent from sufficient exploration".
- P147 and P156 assume a feasible starting policy. P058 uses demonstration cloning. P065's MAPPO-family methods reach only 56.5%.
- **Experiment:** PID-Lagrangian (already in the code: `lambda_mode: pid`). Also warm-start or behaviour-clone from the safe rule policy, which is a feasible starting point by construction.

### 5. Unequal and uncertain budgets, risk sharing, coordinated withdrawal. Easy to Moderate; second contribution
- **Unequal risk across a team:**
  - P165: "how risk should be distributed across heterogeneous team members" is open.
  - P168 lists a "heterogenous team" and "non-binary surviving states" as extensions.
  - P120: "Sauté RL generalizes across safety budgets".
- **Uncertain budgets:**
  - P115: "the radiation lifetime is random".
  - P106: "Significant part-to-part variation in radiation response". This suggests drawing each robot's limit at random.
- **Withdrawals and lost robots:**
  - P182: "ensure that they do not leave the network simultaneously".
  - P178: re-plan "without exposing the surviving robots to more risk".
  - P053: agents could "remain idle" to save resources.
  - P191 and P194: taking over the tasks of lost robots, and planning that accounts for how reliable the remaining robots are.
- **Experiments:**
  - Unequal and randomly drawn budgets, with each robot's remaining budget in its observation (already there).
  - Measure who takes the close-up readings as a function of budget.
  - Measure how spread out the exits are over time.
  - Compare against fixed roles (the Huo P037 style).

### 6. Early-mission vulnerability. Easy analysis
- P167: "initial measurements may fall within hazardous zones before the GP model sufficiently learns".
- P171: small fleets "do not meet a threshold of collected information necessary to direct agents away from hazards".
- **Experiment:** plot violations against the step at which they happen. If they cluster early, add extra margin while the posterior is still wide.

### 7. Stronger non-learned team baselines. Easy
- P213: the "margin of improvement of infotaxis towards the optimal strategy gets smaller", which suggests learning may win only narrowly.
- P038 compares only against other learned methods.
- Candidates: a mutual-information gradient team controller (P033, P180), Voronoi partitioning (P052, P045), Infotaxis + collision avoidance (P057), market-based allocation (P196).
- **Use:** makes "can learning beat the rule" a fair test. Add one, wrapped with the same safety layer.

### 8. Sensor degradation near the source. Easy stress test
- P093: "radiated images cannot be used for visual odometry".
- P109: "LIDAR fail quickly in gamma radiation".
- P106: part-to-part variation.
- **Experiment:** add count noise or dead time that grows with dose rate, and check whether the safety rate holds.

### 9. Future work, out of scope
- Decentralised estimation and limited communication (P080: "robust wireless communication would not be possible in the reactor buildings"; P047, P054, P219, P226).
- Multiple, weak or absent sources (P001, P002, P008).
- Dose-rate-dependent damage (P081: low-dose-rate effects "largely unexplored").
- Stand-off directional sensing (P028).
- Real-robot validation (P111: most models "do not accurately represent real-world environments"; P073 asks for "system-level validation linking component degradation to mission performance").

## What this changes in the thesis plan

1. **Main contribution, strengthened:** idea 1 plus idea 2, i.e. an estimate-based dose safety layer that corrects for model discrepancy. Idea 2 answers an open problem stated in at least nine papers. It also gives the thesis a method contribution that does not depend on whether learning beats the rule.
2. **Second contribution:** idea 5, learned risk sharing with unequal and uncertain budgets.
3. **Cheap experiments to add:**
   - idea 3 (CVaR);
   - idea 4 (PID-Lagrangian, warm start from the rule);
   - idea 6 (when violations happen);
   - idea 7 (one classical team baseline);
   - idea 8 (sensor degradation).
4. **Justify the budget:** 0.1 Gy is about 1000× below the reported hardware failure doses (P078: 111.1 ± 5.5 Gy; controllers about 170 Gy). Present it as a conservative operating limit, and add a budget sweep (0.1, 0.3, 1 Gy) with the activity scaled to match, since only the ratio of budget to activity matters.

## Update: five papers read in full (uploaded PDFs)

Per-paper answers with quotes: `gaps/gaps_fulltext_uploads.json`.

| Paper | Dose budget | Exit / withdraw | Dose from uncertain estimate | Team | Verdict |
|---|---|---|---|---|---|
| P037 Huo 2026 | implicit 30-detection cap tied to "radiation resistance level"; no Gy | none | no (activity assumed known) | 3 robots, fixed roles | static precursor of budget-based roles |
| P042 Ling 2022 | ignored | none | no | 4 identical | – |
| P043 Alagha 2022 | soft movement penalty; "1 cost unit" per agent | agents learn to idle to save resources | no estimator | 1–10 identical, shared policy | weak precursor of withdrawal |
| P079 Zhao 2014 | failure doses: fine under 100 Gy; serial bus abnormal 130 Gy; EEPROM 256 Gy; network dead 270–280 Gy | n/a | n/a | n/a | supports a hard dose resource |
| P118 Gu 2023 | per-agent constraint on expected discounted cost (MACPO hard, MAPPO-L "soft") | none | no (cost from environment) | joints of one robot | generic expected-cost precursor |

**New ideas from these full texts:**
- **Obstacles:** Huo and Ling assume an obstacle-free plane; Ling and Alagha list obstacles as future work. Obstacles make dose path-dependent, which strengthens G1.
- **Hard mask vs expected-cost MARL:** Gu reports that MAPPO-L reacts "with a delay" and is "sensitive to the learning rate". Compare per-episode violation rates and lost reward against MACPO / MAPPO-L.
- **Online, budget-aware roles:** generalise Huo's static split and Alagha's learned idling into learned edge-sensing / probing / withdrawal by remaining budget.
- **Richer damage model:** Zhao shows failure depends on dose rate and power state, comes in soft-then-hard stages, and is partly undone by annealing. This supports component-wise or probabilistic budgets.
- **Lead to check:** Xiao, Cui & Xu 2017 (IEEE T-Cyb), resource-constrained cooperative online search where low-resource agents stop moving.

## Round 2: 194 more papers (citation snowballing)

*10 November 2026.*
- **How they were found:** the references of the 63 relevance-3 papers and the papers citing them, via Semantic Scholar. That gave 3,327 candidates. The 500 with the best keyword scores were screened by title and abstract, and 194 were kept. The library now holds 428 papers.
- **Evidence read:** 99 of the new papers in full text, 84 from the abstract, 11 from the title only.
- **Gap statements:** 537 recorded, with quotes in `gaps/gaps_round2_*.json`.

### Novelty check against the new papers

No new paper combines all four thesis elements. Closest:

| ID | Paper | Has | Lacks |
|---|---|---|---|
| P385 | Dec-MARVEL 2026 (multi-UAV exploration under budget) | multi-robot, hard per-robot budget, guaranteed return reserve, budget-conditioned learned policy | budget is deterministic travel distance, not dose predicted from the searched-for field |
| P323 | Exit-reserve shield for portfolios 2026 | hard budget with a reserved exit cost, projection shield | single agent, finance, uncertainty not about a searched field |
| P307 | CPSS 2026 (cumulative constraints, runtime safety) | remaining cumulative budget turned into a per-step filter on predicted cost | no exit reserve, single agent |
| P343 | Chance-constrained on-orbit inspection 2026 | hard budget by action masking plus a chance constraint | single agent, uncertainty in the dynamics, no exit |
| P337 | Safe exploration in MDPs 2012 | safety = being able to return, judged over the belief | no cumulative budget, single agent |
| P415, P388 | Risk-aware planning in partially known fields (2021, 2024) | risk from a GP posterior of an unknown gas or radiation field (CVaR in P415) | single robot, instantaneous threshold, no cumulative budget or exit |
| P399 | Chance-constrained stochastic orienteering 2024 | prunes actions by sampled probability of exceeding the budget (like the 97th-percentile mask) | single robot, known cost distribution |
| P386 | Risk-bounded multi-agent navigation via iterative risk allocation 2025 | team risk budget split and reallocated across agents | risk is shared and predicted, no exit, no estimated field |
| P306 | Who Bears the Burden? (LiRA) 2026 | learns how a shared constraint is split across agents | expected-value constraint, no exit |
| P269 | Gamma-camera nuclear emergency robot 2022 | dose builds up on the robot while sources are unknown | dose is only a path cost, single robot, no exit |
| P266 | Swarm radiation monitoring 2025 | swarm, robot radiation tolerance evaluated | no per-robot budget enforced, no reserve |

**Effect on the claim:** the claim holds, but **budget + return reserve + learned multi-robot policy is now taken (Dec-MARVEL, P385)**. The thesis must lead with element (3): the cost of every action, including the exit, is predicted from the uncertain estimate of the same source the team is searching for. P411 states the matching gap from the nuclear side: radiation-aware systems "constrain where the robot may go, but never inform the robot where it should look next".

### Recurring problems in round 2 (with examples)
1. **Hard safety within an episode is missing.**
   - Expected-cost or episode-level constraints let rare disasters through (P307, P331, P336, P349).
   - P349: "constraints are risk-neutral, that is, they are only enforced in expectation".
2. **Lagrangian methods are unstable or timid.**
   - P326: "instability due to suboptimal policies and inaccurate Lagrange multipliers".
   - P332: agents "remain still to avoid collisions".
   - P370: "MAPPO-Lagrangian does not guarantee hard constraints for safety".
   - P371: constrained Markov potential games "do not satisfy strong duality".
3. **One-step safety layers ignore forward feasibility.**
   - P376: the safety layer "does not deal with negative long-term consequences of an action".
   - P343: "feasibility masking alone does not ensure safety".
4. **Guarantees rest on calibrated uncertainty, which breaks.**
   - P360: "A primary risk is false confidence".
   - P386: the bound constrains "predicted cumulative risk ... a proxy for ground-truth safety".
   - P323: a support miss terminates the guarantee.
   - P394: hazards "statistically independent across cells".
5. **Splitting a shared constraint across agents is open.**
   - P306: it does not say "how that penalty should be apportioned across agents".
   - P408: how robots "trade-off their local risks with the global/team risk".
   - P410: uniform allocation "is conservative".
6. **When to give up or withdraw is open.**
   - P344: networks "learn how to fall but not when to give up the task".
   - P318: "when recovery should begin".
7. **Nuclear planners assume a known field and treat hazards as no-go zones.**
   - P276: "the radiation intensity is known and remains constant over time".
   - P303: contaminated areas are "mapped but not entered".
   - P270: "commercial electronics require conservative cumulative-dose management".

### New or strengthened ideas (added to the ranked list above)
- **Idea 2 (calibration-aware safety layer) is now supported by about 20 papers.** Concrete forms:
  - Conformal calibration of the dose predictor (P346, P356, P367).
  - A margin that adapts to how accurate the estimator is (P324).
  - A reliability monitor on the filter, e.g. effective sample size or a KL mismatch between predicted and measured counts (P417).
  - A runtime fit-quality gate that "flags when its own assumptions fail" (P236).
- **Risk allocation over time:** spend the dose margin where it buys the most information instead of a fixed 97th percentile every step (P410, P386, P399).
- **Joint consistency of per-robot masks:** independent masks can jointly block the exit, e.g. two robots needing the same doorway (P392, P385). Easy test.
- **Withdrawal as a stopping problem:** predict exit feasibility explicitly and analyse when withdraw is used (P344, P318, P335).
- **Rule plus safety layer as a conservative prior for learning:** warm-start or residual MAPPO that falls back to the rule (P341, P377). This gives a direct route to "beat the rule".
- **Report tail and per-robot violations,** e.g. CVaR of dose and the worst-decile robot (P308, P331).
- **Robustness when teammates withdraw or fail** (P365, P366).
- **State as a contribution:** one source estimate drives both search and safety (P411).
