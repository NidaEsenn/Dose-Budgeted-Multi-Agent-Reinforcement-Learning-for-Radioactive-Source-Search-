# Dose-Budgeted Multi-Agent RL for Radioactive Source Search

A team of robots must localise an unknown, strong (TBq) gamma source while **no
robot exceeds its own cumulative dose budget**. This repository contains the
simulator, the shared particle-filter estimator, rule-based baselines,
MAPPO / MAPPO-Lagrangian (one multiplier per robot) and the full experiment
pipeline for RQ1–RQ3 of the project requirements document.

* Why each component is built the way it is, with the measurements behind
  every choice: [`docs/DESIGN_DECISIONS.md`](docs/DESIGN_DECISIONS.md)
* Requirement-by-requirement status: [`docs/REQUIREMENTS_TRACE.md`](docs/REQUIREMENTS_TRACE.md)
* Things that still need a human to verify: [`docs/OPEN_ITEMS.md`](docs/OPEN_ITEMS.md)

## Run it on your own computer

Needs Python 3.10–3.13 (`python --version`). Takes about 5 minutes.

```bash
git clone https://github.com/NidaEsenn/Dose-Budgeted-Multi-Agent-Reinforcement-Learning-for-Radioactive-Source-Search-.git radsearch
cd radsearch
git checkout feature/core-simulator          # the code lives on this branch for now

python -m venv .venv
source .venv/bin/activate                    # Windows: .venv\Scripts\activate
pip install -e ".[dev]"                      # with Python 3.13 you can use: pip install -r requirements.txt && pip install -e .

python -m pytest -q                          # should print "55 passed"
```

Watch a mission (saves a GIF animation and a PNG of the last frame):

```bash
python scripts/demo.py                                                    # perimeter baseline
python scripts/demo.py --policy models/mappo_sanity_0.1Gy.pt --seed 72    # learned team, strong source
python scripts/demo.py --policy baseline:approach --seed 72 --out approach.gif
```

The first run takes ~30 s longer while Numba compiles its kernels. In the picture:
colours are the true dose rate, grey boxes are obstacles, the green star is the
true source, the white × is the team's estimate, cyan dots are the particle
filter's guesses, and each line is a robot's path with "dose / budget" in the
legend. A faded robot marker means it exceeded its budget and was retired.
Pre-rendered examples are in [`docs/examples/`](docs/examples/).

## Install (cluster / exact versions)

```bash
conda env create -f environment.yml && conda activate radsearch   # or:
pip install -r requirements.txt && pip install -e .
python -m pytest -q          # ~15 s; must pass before every experiment batch (NFR-02)
```

## Quick start

```python
from radsearch.pz_env import RadSearchParallelEnv
env = RadSearchParallelEnv()                 # calibrated main setting (conf/env/main.yaml)
obs, infos = env.reset(seed=0)
while env.agents:
    obs, rew, term, trunc, infos = env.step({a: env.action_space(a).sample() for a in env.agents})
print(infos)                                 # per-robot dose, budget, costs, episode summary
```

## Train

```bash
# MAPPO-Lagrangian, constraint version A, 4 robots, seed 0
python -m radsearch.train algo=mappo_lag_a env=main seed=0
# unconstrained MAPPO / version B / shield / fixed penalty
python -m radsearch.train algo=mappo
python -m radsearch.train algo=mappo_lag_b
python -m radsearch.train algo=mappo_lag_a_shield
python -m radsearch.train algo=mappo_penalty algo.penalty_beta=0.3
# unequal budgets 1:2:4 (RQ3)
python -m radsearch.train algo=mappo_lag_a env=unequal
```

Runs go to `runs/<experiment>/<algo>/<env>/seed<k>/` (config, `metrics.jsonl`,
checkpoints, `eval_test.json`). Interrupted runs resume automatically from
`checkpoints/latest.pt`. W&B logging: `algo.wandb_mode=online|offline|disabled`.

## Evaluate

```bash
python -m radsearch.evaluate --policy runs/.../checkpoints/final.pt --episodes 1000 --grid
python -m radsearch.evaluate --policy baseline:perimeter --episodes 1000
python -m radsearch.evaluate --policy baseline:shielded_greedy,beta=1.0
python scripts/aggregate.py --exp E1 --out docs/results/E1.md      # seeds -> IQM + CIs
```

The test set is fixed: episode *i* uses seed `10_000_000 + i` (room, source,
activity, budgets, measurement noise), identical for every method.

## Experiments on the cluster (SLURM)

```bash
python slurm/make_jobs.py                          # E1–E4 job lists (10 seeds each)
mkdir -p logs
sbatch --array=1-$(wc -l < slurm/jobs/E1.txt)%50 slurm/train_array.sbatch slurm/jobs/E1.txt
sbatch --array=1-120 slurm/eval_array.sbatch E1    # test set, source grid, E5 generalisation
```

## Standalone checks

| script | what it checks |
|---|---|
| `scripts/eval_estimator.py` | particle filter alone, random robots (AC-2, FR-EST-04) |
| `scripts/compare_noise_models.py` | whether the noise model yields a dose/information trade-off |
| `scripts/calibrate.py` | budget calibration: violation rate of dose-unaware search (AC-3) |

## Layout

```
radsearch/
  physics_constants.yaml  every physical constant + source (FR-PHY-07)
  physics.py              dose model, detector model, attenuation (separate functions)
  _kernels.py             Numba-fused attenuation / likelihood kernels (hot path)
  world.py                rooms, obstacles, starts, source placement
  estimator.py            batched particle filter (tempered / regularised / SIR)
  env.py                  batched simulator core (budgets, retirement, rewards, costs)
  pz_env.py               PettingZoo ParallelEnv wrapper
  shield.py               posterior-based dose shield
  baselines/              random, approach, perimeter, greedy, shielded greedy
  algos/mappo.py          MAPPO, MAPPO-Lagrangian (per-robot λ), fixed penalty
  eval/                   metrics (Section 8.1), Wilson / rliable intervals, runner
  render.py               dose-rate heat map + trajectory animation
conf/                     Hydra configs (env/, algo/)
slurm/                    job generator and array scripts
scripts/                  calibration, estimator test, aggregation
tests/                    pytest suite
```

## License

MIT — see [LICENSE](LICENSE).
