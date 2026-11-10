# Gap analysis: where the thesis is new

*10 November 2026 (updated with full-text reads of P037, P042, P043, P079, P118). Based on 234 papers in `papers.csv` (IDs P###). Evidence level: abstracts for almost all papers; full-text passages for two (P233 RICA, P234 Sayed) via Scholar Gateway. The full texts of the closest works could not be fetched from this environment (publisher hosts blocked); the checks still owed are listed at the end.*

## Bottom line

The thesis is new where four research lines meet, and **not** in any one of them. Each line already has its own piece:

| Line | Already done | Not done |
|---|---|---|
| Radiation search with robots (A, B) | Single- and multi-robot search with particle filters and (MA)RL: Proctor P005, Totten P003, PSOPF-MATD3 P038, Huo P037 | The searcher's own dose is never a constraint |
| Nuclear robotics (C) | Robot dose minimised as a cost (West P004, Groves P006, Batty P074); dose tracked like a worker's dose to plan maintenance (RICA P233); missions sized offline from dose tolerance (Nagatani P080) | No online, hard per-robot budget with a reserved exit |
| Budgeted exploration (E) | "Keep enough to get home" with a non-renewable resource: Eclares P169, Tiwari P176, Shamshirgaran P173; team routing with survival constraints (Jorgensen P178) | The cost is known or estimated from the robot's own wear, not from the unknown field being searched for |
| Hazard-aware information gathering (F, E) | The hazard is unknown and learned while searching; information is traded against robot loss (Schwager P180, Dames P207, McGuire P171, Srivastava P164, Butler P165) | Loss is a per-step probability; no cumulative budget, no exit |
| Safe MARL (D) | Per-agent constraints and masks (Gu P118, Elsayed-Aly P124, SEA-MAPPO P117); budget-in-state theory (Saute P120, Castellano P125) | Masks rely on known or near-known cost models |

**The defensible gap:** *safe cooperative search in which the cost of every action (dose) is predicted from the same uncertain belief the team is trying to improve, under a hard, non-renewable, per-robot budget that must also cover the way out.*

## Candidate gaps, ranked

### G1. Estimate-coupled safety constraint (strongest)
- **Claim:** the safety check "dose so far + next step + exit ≤ budget" uses dose predicted from the source posterior, so safety depends on estimation quality, and gathering information both improves and spends the safety margin.
- **Closest:** Schwager P180 and Dames P207 couple hazard and information, but with failure probabilities, not a budget. SEA-MAPPO P117 masks with a learned *energy* predictor that does not depend on the searched-for field. Safe exploration with an unknown cost (Turchetta, Wachi in cluster D) is single-agent and has no cumulative budget.
- **What could weaken it:** a radiation paper that predicts its own dose from the source estimate. None was found in the abstracts. RadDQN (Sadhu 2024) could not be verified and must be checked.
- **Evidence the thesis already has:** the posterior-mean rule gives 14.7% violations, the 97th-percentile rule 4.3%, and the filter's 90% region holds the source only 52–65% of the time. Uncertainty about the estimate is what decides safety.

### G2. Hard per-robot budget with exit reserve in radiation search
- **Claim:** first online, hard, per-robot cumulative-dose constraint with a reserved exit for radiation search.
- **Closest:** RICA P233 shows the practice ("the cumulative dose absorbed by the robot can be followed by dosimetry, as is done for human operators") but uses it only for maintenance planning. Nagatani P080 sized the mission offline. West P004 and Batty P074 minimise dose softly. Lee P041 is multi-agent with evacuation, but in a known field.
- **What could weaken it:** "budget + return" is standard in energy-aware robotics (P169, P176, P173). On its own it reads as "energy-aware planning with dose instead of battery". **G2 is only strong together with G1** (the cost depends on the unknown field).

### G3. Learned risk allocation in teams with unequal budgets (good, but crowded in 2026)
- **Claim:** a team learns who takes the close-up measurements and who withdraws, depending on remaining budgets, instead of fixed roles.
- **Closest:**
  - Huo P037 and Ling P039 assign fixed roles by radiation tolerance.
  - Butler P165 (arXiv 2026) gives a game-theoretic risk transfer to lower-valued robots, with exposure as a penalty.
  - Jorgensen P178 and Simon P168 handle known per-edge risks.
  - McGuire P171 values lost robots.
- **Huo P037, checked in full text (10 Nov):** roles are fixed before the mission (two static low-tolerance robots at the edge, one high-tolerance mobile robot). Tolerance is never given in Gy and no robot dose is computed; the "residence time K" is a 30-detection stop. There is no exit, reserve or withdrawal. **Not a threat:** cite it as the static, qualitative precursor of budget-dependent roles.
- **Still to check:** Butler P165 (game-theoretic risk transfer). Also Xiao, Cui & Xu 2017, "cooperative multiagent online search with resource constraints" (IEEE Trans. Cybernetics), cited by Alagha P043: there, agents whose resources are "much less than the average of the team ... decide not to move". That is allocation under unequal resources and possible prior art for G3.
- **Still open:** learned (MARL) allocation, a cumulative budget (not penalty or probability), voluntary withdrawal, and an uncertain cost.

### G4. Why price-based safe RL fails here (supporting finding)
- **Claim:** Lagrangian or penalty methods become timid when the cost and the information are in the same place. The robots stop approaching, so the estimate never improves.
- **Closest:** Stooke (PID Lagrangian) and Peng (over-conservatism under chance constraints) in cluster D report oscillation and conservatism in general, but not this mechanism.
- **What it needs:** several seeds and a mechanism analysis, for example showing that λ rises before the information gain stops. Today it rests on single runs under the earlier rules. **Do not use it as a main contribution until those runs exist.**

### G5. Calibration of the estimator as a safety quantity (supporting finding, new angle)
- **Claim:** an overconfident posterior (correlated model error treated as independent) breaks a belief-based safety layer, and calibration trades directly against mission success.
- **Closest:** Brynjarsdottir & O'Hagan (model discrepancy, cluster F) explains the overconfidence, but no robotics paper found links filter calibration to the safety rate of exploring robots.
- **Evidence:** D24 sweep (13 settings, none better on both axes).

## Recommended framing

**Main contribution (G1 + G2):** a formulation and safety layer for cooperative radiation search in which each robot's hard dose budget, including its exit reserve, is checked against dose predicted from the team's uncertain source estimate, with a pessimistic quantile. The evidence: it makes the 5% target reachable where the mean-based rule and price-based RL do not.

**Second contribution (G3), if the full-text checks allow it:** learned, budget-dependent risk sharing and withdrawal in teams with unequal budgets.

**Supporting findings:** G4 (timidity of price-based methods) and G5 (calibration matters for safety).

Draft one-sentence positioning:
> Prior radiation-search work ignores the searcher's own dose, nuclear robotics minimises it without a hard limit, energy-aware robotics reserves a return trip under a known cost, and hazard-aware information gathering models robot loss as a probability; we study cooperative search under hard, non-renewable, exit-coupled dose budgets whose cost must be predicted from the same uncertain source estimate the team is refining.

## What reviewers are likely to say, and the answer

| Objection | Answer |
|---|---|
| "This is SEA-MAPPO with dose instead of battery." | SEA-MAPPO's cost predictor is learned from the robot's own power use and does not depend on the target. Here the cost depends on the unknown source. The mean-vs-quantile result (14.7% vs 4.3%) shows that this changes what a safe mask needs. |
| "This is Schwager 2016 with a budget." | Schwager models loss as a per-step probability and has no exit. A cumulative budget makes the problem path-dependent (each step's dose stays), and the exit reserve makes it state-dependent. |
| "Budget + return is old (energy-aware planning)." | Yes, and we cite it. What is new is that the cost of the return depends on the estimate being formed, so the reserve shrinks or grows as the belief changes. |
| "A simple rule already works; why RL?" | Open, and the thesis's main experiment (P1 pilot). The rule only moves along the safety–success trade-off. Whether learning moves it outward is the question. |

## Still owed before the claims are final

Read in full. They can't be fetched from here; download them or allow the hosts:

| Paper | Why | Host |
|---|---|---|
| ~~P037 Huo et al. 2026, Heterogeneity~~ | Done (full text): not a threat, see G3 | – |
| P165 Butler et al. 2026, Algorithmic altruism | Overlap with G3 | arxiv.org/abs/2608.28409 |
| Xiao, Cui & Xu 2017, cooperative multiagent online search with resource constraints (IEEE T-Cyb) | Possible G3 prior art (unequal resources, agents stop moving) | IEEE (Northeastern access) |
| P003 Totten 2023, RAD-TEAM | Confirm no dose budget or exit | pdxscholar.library.pdx.edu (open PDF) |
| P117 Abdelmeguid & Hasan 2026, SEA-MAPPO | Exact predictor and mask design, for the related-work contrast | mdpi.com (open) |
| P180 Schwager et al. 2016 | Exact failure model | Springer or an author copy |
| P164 Srivastava et al. 2026 | Information-vs-risk framing | arxiv.org/abs/2609.10726 |
| RadDQN, Sadhu et al. 2024 (not in library) | Possible overlap with G1 | arXiv or IEEE |
| Srivastava et al. 2025, Behaviorally Adaptive Multi-Robot Hazard Localization (not in library) | Possible overlap with G1/G3 | arXiv |

Either allow these hosts in the environment's network settings (arxiv.org, doi.org, www.mdpi.com, www.sciencedirect.com, papers.ssrn.com, pdxscholar.library.pdx.edu), or download the PDFs and add them to the repo (e.g. `docs/literature/pdf/`, not committed if the licence forbids it).
