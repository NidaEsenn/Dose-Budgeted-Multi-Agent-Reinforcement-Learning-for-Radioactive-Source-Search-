# Running on the university HPC cluster

The training code is **CPU-bound**: the simulator and particle filter are
NumPy/Numba, and the policy is a 2-layer MLP with 128 units. A GPU (H100/H200)
gives almost no speed-up and wastes allocation. Ask for **CPU nodes**, and run
many seeds side by side as a job array.

Measured speed (this container, 1 run, 16 envs):

| Algorithm | env steps / s | 2 M steps |
|---|---|---|
| `mappo` | ~455 | ~1.2 h |
| `mappo_lag_b` | ~450 | ~1.3 h |
| `mappo_reserve` (reserve shield in the loop) | ~113 | ~5 h |

`slurm/train_array.sbatch` asks for 8 CPUs, 8 GB and 12 h per run; requeue
and resume from `checkpoints/latest.pt` are built in.

## 1. Log in

Use the cluster's login node (check the research computing docs for the
current host name and whether you need the VPN off campus). Do not run
training on the login node.

```bash
ssh <username>@<login-host>
```

## 2. Get the code and the environment (once)

```bash
git clone https://github.com/NidaEsenn/Dose-Budgeted-Multi-Agent-Reinforcement-Learning-for-Radioactive-Source-Search-.git radsearch
cd radsearch
git checkout feature/core-simulator

module load miniconda3        # or anaconda3; check `module avail conda`
conda env create -f environment.yml -n radsearch
conda activate radsearch
pip install -e '.[dev]'
```

Check it works, on a compute node, not the login node:

```bash
srun --cpus-per-task=4 --mem=8G --time=00:30:00 --pty bash
conda activate radsearch
python -m pytest -q tests          # 76 tests, about 1-2 minutes
exit
```

## 3. Pick the partition

```bash
sinfo -s                 # partitions and their time limits
```

Use a CPU partition that allows at least 12 h. Add it to the sbatch line
with `--partition=<name>`. If its limit is shorter, keep the limit: jobs
requeue themselves and resume from the last checkpoint.

## 4. Run the pilot (P1: 9 runs)

```bash
mkdir -p logs
sbatch --partition=<cpu-partition> --array=1-9 slurm/train_array.sbatch slurm/jobs/P1.txt
squeue -u $USER          # watch the jobs
tail -f logs/radsearch_<jobid>_1.out
```

P1 = `mappo`, `mappo_reserve`, `mappo_lag_b` × 3 seeds, under the current
rules (withdraw on, 0.1 Gy, 10–100 TBq). Each run evaluates itself on 1000
test missions at the end: `runs/P1/<algo>/main/seed<k>/eval_test.json`.

## 5. Bring the results back

From your own computer:

```bash
rsync -av <username>@<login-host>:radsearch/runs/P1/ runs/P1/ \
  --include='*/' --include='eval_test.json' --include='metrics.jsonl' \
  --include='final.pt' --include='config.json' --exclude='*'
```

Or commit only the small JSON files from the cluster and push them. Then
`python scripts/aggregate.py --exp P1 --tag test` compares the runs.

## Later: the full matrix

`python slurm/make_jobs.py` writes `slurm/jobs/E1.txt` … `E4.txt` (370 runs).
These still follow the old plan (MAPPO-L as the main method) and will be
rewritten after the pilot (Karar 3).
