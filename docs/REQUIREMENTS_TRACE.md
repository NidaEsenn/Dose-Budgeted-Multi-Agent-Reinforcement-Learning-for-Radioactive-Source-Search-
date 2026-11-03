# Requirements traceability

Status: **done** = implemented and covered by a test or a recorded run;
**ready** = implemented, needs the HPC runs to produce results;
**deviation** = implemented differently from the PRD text, reason in DESIGN_DECISIONS;
**open** = not implemented (semester 2 / Could).

## Environment (ENV)
| ID | Status | Where / evidence |
|---|---|---|
| FR-ENV-01 PettingZoo ParallelEnv + parallel_api_test | done | `radsearch/pz_env.py`, `tests/test_env.py::test_parallel_api` |
| FR-ENV-02 20×20 grid, 0–7 rectangles | done | `world.generate_layout`; non-overlapping, connected (D4) |
| FR-ENV-03 3/4/6 robots | done | `EnvConfig.n_agents`, `tests/test_env.py::test_obs_shapes` |
| FR-ENV-04 5 actions, blocked moves stay | done | `tests/test_env.py::test_moves_into_obstacles_stay` |
| FR-ENV-05 step time 10 s, 200-step limit | done | `EnvConfig.step_time/max_steps` |
| FR-ENV-06 reproducible seeds | done | `test_seed_reproducible`, `test_batch_independent_of_composition` |
| FR-ENV-07 batched execution | done | `RadSearchCore(n_envs=B)` (D5) |
| FR-ENV-08 heat map + trajectory animation | done | `radsearch/render.py`, `test_render` |
| FR-ENV-09 random / 1 m grid source placement | done | `world.sample_source`, `world.source_grid`, `evaluate.evaluate_grid` |
| FR-ENV-10 curriculum | done | `AlgoConfig.curriculum` (stages override any EnvConfig field) |
| FR-ENV-11 continuous motion | open | semester 2 |

## Physics (PHY)
| ID | Status | Where / evidence |
|---|---|---|
| FR-PHY-01 Γ·A/r² × wall attenuation | deviation | `physics.dose_rate`; adds detector height and (configurable) air attenuation (D14, D15) |
| FR-PHY-02 dose = rate × dt, cumulative | done | `test_step_dose_is_rate_times_dt`, `test_dose_accumulates_and_retirement` |
| FR-PHY-03 Poisson counts, Wright/Son detector model | deviation | `physics.expected_counts`; adds the model-error field (D6) |
| FR-PHY-04 separate dose / detector functions | done | `physics.dose_rate`, `physics.expected_counts` |
| FR-PHY-05 path length through obstacles | done | exact slab clipping, `test_chord_matches_dense_sampling` (D2) |
| FR-PHY-06 Cs-137 / Co-60, 1–100 TBq log-uniform | done | `EnvConfig.isotope/activity_TBq` |
| FR-PHY-07 one constants file with sources | done | `radsearch/physics_constants.yaml`, `test_constants_have_sources` |
| FR-PHY-08 dead time | done | `detector.dead_time_s` (off by default), `test_dead_time_saturates` |
| FR-PHY-09 OpenMC spot-check | open | semester 2 |

## Budgets (BUD)
| ID | Status | Where / evidence |
|---|---|---|
| FR-BUD-01 per-robot budget 0.2–2 Gy | done | `budget_base_Gy`, `budget_base_range` |
| FR-BUD-02 equal / unequal (1:2:4) | done | `budget_ratio`, `test_unequal_budgets_keep_mean` |
| FR-BUD-03 retirement at budget | done | `test_retired_robot_does_not_move` |
| FR-BUD-04 masked actions, excluded steps | done | `core.action_mask`, `acting` mask in every loss (`algos/mappo.py`) |
| FR-BUD-05 per-episode dose / violation / when | done | `RadSearchCore.episode_info` |

## Estimator (EST)
| ID | Status | Where / evidence |
|---|---|---|
| FR-EST-01 shared PF over (x, y, A), 2000–5000 particles | done | `radsearch/estimator.py` (tempered variant, D3) |
| FR-EST-02 same model as simulator | done | fused kernel tested equal to `physics` (`test_fused_*`) |
| FR-EST-03 posterior mean + covariance | done | `ParticleFilter.estimate` |
| FR-EST-04 testable alone | done | `scripts/eval_estimator.py`, `tests/test_estimator.py` |
| FR-EST-05 multi-source | open | semester 2 |

## Observations & rewards (OBS)
| ID | Status | Where / evidence |
|---|---|---|
| FR-OBS-01 observation contents | done (+3 features) | `RadSearchCore.observe`; adds dosimeter rate, time left, free run-lengths (D13) |
| FR-OBS-02 critic sees true source | done | centralised `state` |
| FR-OBS-03 team reward: error reduction − time + success bonus | done | `RadSearchCore.step` |
| FR-OBS-04 dose not in reward for constrained method | done | `dose_penalty_beta = 0` except `mappo_penalty` |
| FR-OBS-05 success = estimate within 1 m | done | `success_radius` |
| FR-OBS-06 information-gain reward | open | semester 2 |

## Algorithms (ALG) and baselines (BSL)
| ID | Status | Where / evidence |
|---|---|---|
| FR-ALG-01 MAPPO, shared params + ID, central critic | done | `algos/mappo.py` |
| FR-ALG-02 cost critic + per-robot λ | done | `Lagrange`, `ActorCritic.ccritic` |
| FR-ALG-03 version A (dose, 75 %) | done | `conf/algo/mappo_lag_a.yaml` |
| FR-ALG-04 version B (indicator, 0.05, + κ dose) | done | `conf/algo/mappo_lag_b.yaml` |
| FR-ALG-05 fixed penalty β sweep | done | `conf/algo/mappo_penalty.yaml`, `slurm/make_jobs.py` |
| FR-ALG-06 λ update matches Safe-Policy-Optimization | done | `test_lagrange_gd_matches_safe_policy_optimization_rule` (rule reproduced from its source; code not diffed, see OPEN_ITEMS) |
| FR-ALG-07 shield in front of policy | done | `radsearch/shield.py`, `conf/algo/mappo_lag_a_shield.yaml` |
| FR-ALG-08 MACPO / Def-MARL | open | semester 2 |
| FR-BSL-01..05 | done | `radsearch/baselines/policies.py`, `tests/test_baselines.py` (incl. "never reads the true source") |
| FR-BSL-06 PF planner | open | semester 2 |

## Infrastructure, evaluation, release
| ID | Status | Where / evidence |
|---|---|---|
| FR-INF-01 Hydra configs | done | `conf/`, `radsearch/train.py` |
| FR-INF-02 SLURM arrays | ready | `slurm/` (not run: no cluster in this session) |
| FR-INF-03 checkpoints + auto-resume | done | atomic `latest.pt`, `test_train_resume_and_eval`, SLURM requeue on USR1 |
| FR-INF-04 W&B logging | done | `Logger` (W&B + always-on `metrics.jsonl`) |
| FR-INF-05 pinned environment | done | `requirements.txt`, `environment.yml` |
| FR-EVAL-01 10 seeds | ready | `slurm/make_jobs.py` |
| FR-EVAL-02 fixed 1000 test rooms + source grid | done | `eval/runner.py`, `evaluate.evaluate_grid` |
| FR-EVAL-03 rliable + Wilson | done | `eval/metrics.py`, `scripts/aggregate.py` |
| FR-EVAL-04 decision time | done | `run_episodes(time_decisions=True)` |
| FR-EVAL-05 generalisation | ready | `slurm/eval_array.sbatch` (more robots, high activity, dense maps) |
| FR-REL-01 public code, MIT, README | ready | LICENSE, README (repository visibility is the author's call) |
| FR-REL-02..04 | open | after experiments |
| NFR-01 reproducibility | done | seed tests |
| NFR-02 unit tests gate batches | done | 55 tests; SLURM task 1 runs pytest |
| NFR-03 < 12 h per run | on track | ~210 env-steps/s on 4 CPUs → 2 M env steps ≈ 2.6 h (D5) |
| NFR-04 environment freeze | process | tag `env-v1.0` at week 8 |

## Acceptance criteria
| ID | Status | Evidence |
|---|---|---|
| AC-1 API + unit tests | met | 55 tests pass |
| AC-2 PF localises with random robots, empty room | met | tempered PF 100 % success (D3) |
| AC-3 MAPPO violates ≥ 30 % | **not met** | 9 % at 0.1 Gy (D18); recalibrate |
| AC-4 MAPPO beats random & perimeter | partial | beats random; ties perimeter (1 seed, 300 k steps) |
| AC-5 λ converge | pending | needs version B with d/N split (D19) |
| AC-6, AC-7 | pending | HPC runs |
