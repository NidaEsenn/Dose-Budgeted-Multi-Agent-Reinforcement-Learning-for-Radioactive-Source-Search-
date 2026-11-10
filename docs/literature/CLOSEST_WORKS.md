# Closest works and first novelty check

*Search of 10 November 2026: 232 unique papers in six clusters (see `README.md`). A random sample of 20 DOIs was re-checked in OpenAlex: 20/20 exact matches. This page lists only the papers that overlap most with the thesis; the full novelty analysis comes next.*

**First result:** no paper found combines all four thesis elements:
1. a **cumulative, non-renewable dose budget** for each searching robot,
2. a **reserve for the exit trip**,
3. dose predictions that depend on the **uncertain estimate of the source being searched for**, and
4. **multi-robot** coordination (learned or rule-based), with withdrawal and risk sharing.

This rests on titles and abstracts. Papers marked "full text" below must be read before the claim is stated in the thesis.

## Overlap matrix

Columns: **Dose** = robot's own cumulative dose is limited (B = hard budget, S = soft cost, P = failure probability, – = ignored). **Exit** = return trip is reserved. **Unc** = the cost depends on an uncertain, estimated field. **Multi** = several robots. **Learn** = learned policy.

| ID | Paper | Dose | Exit | Unc | Multi | Learn | Read full text? |
|---|---|---|---|---|---|---|---|
| P117 | Abdelmeguid & Hasan 2026, SEA-MAPPO (battery, Robotics) | B (battery) | – | – (energy roughly known) | yes | MAPPO | yes: closest method |
| P038 | Huo et al. 2025, PSOPF-MATD3 (NET) | – | – | – | yes | MATD3 | no |
| P003 | Totten 2023, RAD-TEAM MARL (PSU thesis) | – | – | – | yes | MARL | yes: confirm no budget |
| P037 | Huo et al. 2026, Heterogeneity (Prog. Nucl. Energy). **Full text read** | implicit: "residence time ... constrained by its radiation resistance level", in practice a 30-detection stop; no Gy, no dose computed | – (mobile robot "ultimately moves to the source location") | – (activity assumed known; estimate drives information gain only) | 3 robots, roles fixed by design | rule | done |
| P039 | Ling et al. 2024, heterogeneous search (Ann. Nucl. Energy) | ? | – | ? | yes | rule | yes |
| P041 | Lee et al. 2023, multi-agent min-dose path planning (NET) | S | evacuation | – (known field) | yes | – | no |
| P074 | Batty 2026, radiation-aware navigation (Liverpool PhD) | S | ? | GP map | no | – | yes |
| P004 | West et al. 2022, layered costmaps (Frontiers) | S | – | map | no | – | no |
| P006 | Groves et al. 2021, radiation-informed exploration (Robotics) | S | – | map | no | – | no |
| P080 | Nagatani et al. 2012, Fukushima robots (JFR) | offline budget | – | – | – | – | no |
| P001 | Son et al. 2026, physics-guided localization (T-ASE) | avoids approach | – | yes | no | – | no |
| P047 | Zhou et al. 2026, CPE-Infotaxis multi-robot (NET) | motivation only | – | yes | yes | – | yes |
| P180 | Schwager et al. 2016, information gathering with unknown hazards | P | – | yes (hazard learned) | yes | – | yes: closest idea |
| P207 | Dames et al. 2012, decentralized hazardous information gathering | P | – | yes | yes | – | no |
| P171 | McGuire et al. 2024, valuing attrition (IROS) | P | – | yes | yes | – | yes |
| P164 | Srivastava et al. 2026, when information is worth the risk (arXiv) | P | – | yes | yes | – | yes |
| P165 | Butler et al. 2026, algorithmic altruism (arXiv) | S (expected exposure) | – | ? | yes, heterogeneous | – | yes: risk sharing |
| P178 | Jorgensen et al. 2017, Team Surviving Orienteers | P (survival constraint) | – | – (known edge risks) | yes | – | no |
| P169 | Naveed et al. 2024, Eclares (ICRA) | B (energy) | **yes** (return to charger) | – | no | – | no |
| P173 | Shamshirgaran & Carpin 2022, field mapping under budget (IROS) | B (energy) | **yes** (reach final site) | stochastic energy | no | – | no |
| P176 | Tiwari et al. 2018, operational range on one discharge | B (energy) | **yes** | estimated | no | – | no |
| P120 / P125 | Sootla 2022 Saute RL; Castellano 2021 almost-sure constraints | budget in state | – | – | no | yes | no (theory support) |
| P124 | Elsayed-Aly et al. 2021, shielded MARL (AAMAS) | shield | – | – (known model) | yes | yes | no |

### Added in round 2

| ID | Paper | Dose | Exit | Unc | Multi | Learn |
|---|---|---|---|---|---|---|
| P385 | Dec-MARVEL 2026 | B (travel distance) | **yes** | – | yes | MARL |
| P323 | Exit-reserve shield (finance) 2026 | B (drawdown) | **yes** | return set, not a field | no | yes |
| P307 | CPSS 2026 | B (cumulative safety budget) | – | predicted cost | no | yes |
| P399 | Chance-constrained orienteering 2024 | B, chance-pruned | – | known cost distribution | no | MCTS |
| P386 | Iterative risk allocation, multi-agent 2025 | shared risk budget | – | predicted risk | yes | – |
| P415 / P388 | Risk from GP field estimate 2021 / 2024 | threshold | – | **yes** | no | – |
| P269 | Gamma-camera emergency robot 2022 | S | – | yes | no | – |

## Where the gap looks real

- **Nuclear robotics** treats dose as something to minimise (soft cost) or plans an offline time limit. No paper found enforces a hard per-robot budget online with a reserved exit.
- **Hazard-aware multi-robot information gathering** (Schwager, Dames, McGuire, Srivastava) is the closest *idea*: the hazard is unknown and learned while searching. But robot loss is a per-step probability, not a cumulative budget, and there is no exit.
- **Energy-aware exploration** has exactly the "budget must cover the return" structure (Eclares, Tiwari, Shamshirgaran). But the cost does not depend on the unknown field being searched for.
- **Safe MARL** has per-agent constraints and shields (Gu, Elsayed-Aly, SEA-MAPPO), but with known or roughly known cost models and expected-cost constraints.

The thesis sits where these four lines meet. Its sharpest distinguishing point is **the cost of every action depends on the same uncertain estimate the team is trying to improve.**

## Leads seen but not verified in OpenAlex (find by hand)

- Sadhu et al. 2024, RadDQN: minimum-exposure pathway DQN (IEEE TNNLS). **Check: may be close.**
- Srivastava et al. 2025, Behaviorally Adaptive Multi-Robot Hazard Localization in Failure-Prone, Communication-Denied Environments (arXiv). **Check: may be close.**
- Proskurin et al. 2026, Asymmetric Radiation-Aware Navigation for Mobile Robots in Constrained Environments (SSRN; keywords mention total ionizing dose).
- Romanchek 2021 (stopping criteria for single-detector search); Park 2023 (receding-horizon infotaxis); Rhodes 2022 (dual-control source-term estimation, UAV).
- Spoor et al. 2025 (Lagrangian methods in safe RL); Hamel-De le Court et al. 2025 (probabilistic shielding with state augmentation); Zhang et al. 2024 (CVaR-constrained policy optimisation).
- Shi et al. 2020, Robust Multiple-Path Orienteering Problem (T-RO).
- Altman 1999 (CMDP book) and Ray et al. 2019 (Safety Gym) did not resolve in OpenAlex but are standard references.

## Radiation tolerance numbers (for justifying the 0.1 Gy budget)

From abstracts in cluster C: a ROS single-board computer fails at 111.1 ± 5.5 Gy (P078, West 2021); robot controllers damaged above 170 Gy (Chang 2024); a COTS HD camera still works after about 80 Gy (Wang 2018); laser rangefinders fail abruptly at low dose (Diggins 2014). COTS robot electronics therefore fail at roughly 100–200 Gy, weak parts lower. The 0.1 Gy budget is a deliberately conservative modelled operating limit, not a failure dose.
