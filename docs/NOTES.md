# Thesis project notes

*Last updated: 8 November 2026. Code is on branch `feature/core-simulator`.*

## Where things stand

The simulator, estimator, baselines, learning methods (MAPPO, MAPPO-Lagrangian), evaluation pipeline and a MuJoCo 3D world are built and tested (68 automated tests). Short training runs work. The main open problem: under the current rules, no strategy, learned or hand-written, can keep budget violations under the 5% target. The task definition needs one more change before the full experiments.

## Decisions waiting

1. **Withdraw action (needs my decision).** Let a robot low on budget drive out and stop collecting dose. Recommended, maybe together with a 0.2 Gy budget. Reason: at 100 TBq and 0.1 Gy, a robot standing at the door uses its whole budget in about 4 minutes, and robots currently can't leave early.
2. **Budget level.** 0.1 Gy meets AC-3 but is below the requirements' 0.2–2 Gy range. Flag to the advisor.
3. **For the advisor:**
   - Is the realistic detector-error model (about 30%, location-dependent) acceptable, and from which literature source?
   - Is option (b), "a robot must be able to get out", the right definition of safe?
   - Which contribution to emphasize (benchmark, method, application), and which venue?
   - Should someone from nuclear engineering check the simulator's realism?
   - Real-robot testing route (simulated radiation on real robots, light source as analogy, low-activity check source)?
   - Cluster access, meeting rhythm.
4. **Tell the advisor that the prototype was built with an AI coding assistant.** Make sure I can explain every part.

## Key findings so far

All single training runs; preliminary.

| Finding | Numbers |
|---|---|
| A perfect sensor makes the problem trivial; realistic location-dependent error restores the trade-off | Going close: 96% success vs 81% staying far (30% error); no error: both ~63% |
| Going close pays | 95% success when a robot came within 2 m, 73% otherwise |
| The trained team sends one "scout" on its own | ~1 robot per mission vs ~3 for the "everyone approach" rule |
| Without a safety rule, robots get stranded | 29% of missions over budget, 12% with a stranded robot (0.1 Gy, 10–100 TBq, exit required) |
| Every violation came from strong sources | 0% below 10 TBq, 36% at 30–100 TBq (old rules) |
| The safe version became too timid | MAPPO-L: 10% success, 6–7% violations, robots stay ~13 m away, missions hit the 200-step limit |
| Fixes helped only partly | Warm start + slower λ: still 10% success; + shield: 34% |
| The target is currently unreachable for everyone | Best hand-written strategy (shielded greedy): 9% violations; perimeter: 19.5% |
| Grid policy transfers to 3D physical motion if robots keep pace | 93% success at 0.5 m/s, 83% at 0.08 m/s |

Fixed bugs: the per-robot 5% limit is now split across the team (5% ÷ 4); λ is updated from real violations only, not from the per-step dose hint.

## Next steps, in order

1. Decide on the withdraw action and budget (above).
2. Implement it; check with the baselines that ≤5% violations is reachable and that the unsafe team still violates often (AC-3).
3. Retrain the safe version (warm start, slower λ, with and without the shield).
4. Get cluster access; run the full experiments (10 seeds, ~370 runs).
5. Later: better risk-sharing metric for RQ3 (dose-share slope, budget-shuffle test), detector-error sweep 0–30%, ROS 2 + Gazebo on a local Ubuntu machine, randomized robot speed in training.

## Publication plan

The official pages were blocked here; deadlines come from search results. Confirm each on the live call.

| Venue | Type | When | Notes |
|---|---|---|---|
| ICRA 2027 workshops | 2–4 page extended abstract, IEEE template | Calls in spring 2027 | Robotics angle; draft ready |
| ICLR 2027 workshops | ~4 page paper, usually non-archival | Workshops 29–30 Apr 2027; list out ~late Nov 2026 | ML angle ("when constraints can't be met"); draft ready |
| ANS Annual Conference 2027 | 1–4 page summary on the ANS template, title ≤10 words | Deadline: check the call | Needs final results; draft opening + plan ready |
| IEEE NSS-MIC 2027 | Abstract | Historically early May | Detector-model angle; draft ready |
| NPIC&HMIT + ISOFIC 2027 (ANS) | Conference paper | Abstract 20 Nov 2026 | Loose fit; probably skip |
| Sensors (MDPI) special issue "Advanced Sensors and Robotics for Radiological Environments" | Journal | Deadline unknown: check | Good fit if still open |
| AAMAS 2027 | — | Closed | No extended abstracts in 2027 |

**Journals (any time, once full results exist):** Nuclear Engineering and Technology (published the two closest papers), IEEE Transactions on Nuclear Science, Journal of Nuclear Engineering (published RAD-A2C), Frontiers in Robotics and AI, IEEE RA-L. Post an arXiv preprint at submission time.

**Plan:** a workshop or ANS summary in spring 2027, then a journal paper with the complete results around semester 2.

## Resume entry

```latex
\resumeSubheading
  {Northeastern University}{Boston, MA}
  {Master's Thesis Research (Advisor: Prof. [Name])}{Sep. 2026 -- Present}
  \resumeItemListStart
    \resumeItem{\normalsize{Developing constrained multi-agent reinforcement learning (MAPPO with per-robot Lagrangian dose constraints, PyTorch) so robot teams can locate radioactive sources without any robot exceeding its radiation budget.}}
    \resumeItem{\normalsize{Built a physics-based multi-robot simulator (PettingZoo, Numba) with particle-filter source estimation and a MuJoCo 3D motion layer for sim-to-sim transfer tests; exports missions to Gazebo for ROS 2 integration.}}
  \resumeItemListEnd
```

Fill in the advisor's name and the real start date. Add SLURM only after running on the cluster, and ROS 2 only after the bridge works.

## Documents and files

| What | Where |
|---|---|
| 10-slide presentation | `docs/progress_presentation_10.pptx` |
| 21-slide presentation (with backup) | `docs/progress_presentation.pptx` |
| Project overview (web) | `docs/project_overview.html` |
| Decision brief for the advisor | `docs/advisor_decisions.html` |
| Decision log (Turkish, start → current decisions) | [Claude doc](https://claude.ai/artifact/VwwRwrpWm4DoecbmFTY2P5) |
| Abstract drafts per venue | [Claude doc](https://claude.ai/artifact/7N77MofsyEFnAkqPiHwXBv) |
| Design decisions with measurements | `docs/DESIGN_DECISIONS.md` |
| Requirement-by-requirement status | `docs/REQUIREMENTS_TRACE.md` |
| Items to verify | `docs/OPEN_ITEMS.md` |
| ROS 2 / Gazebo setup guide | `docs/ROS2_GAZEBO.md` |
| Example animations and 3D stills | `docs/examples/` |
| Trained models | `models/` |

Run a demo: `python scripts/demo.py --policy models/mappo_sanity_0.1Gy.pt --seed 72` (3D: `scripts/demo3d.py`).

## Things to verify by hand

- Detector formula symbols against Wright et al. (2021).
- NIST XCOM attenuation values in `radsearch/physics_constants.yaml`.
- A literature value for the detector-error size (σ ≈ 0.2–0.3).
- Goiânia 50.9 TBq, Mexico 111 TBq and the other incident numbers in the IAEA reports.
- Licence of the Goiânia source photo on Wikimedia Commons, if I use it.
- Each venue's policy on AI-assisted writing and code.
