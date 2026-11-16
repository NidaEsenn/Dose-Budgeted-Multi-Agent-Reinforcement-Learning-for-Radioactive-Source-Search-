#!/bin/bash
# One training run per array task (FR-INF-02). Usage:
#   sbatch --array=1-$(wc -l < slurm/jobs/E1.txt)%50 slurm/train_array.sbatch slurm/jobs/E1.txt
#SBATCH --job-name=radsearch
#SBATCH --cpus-per-task=8
#SBATCH --mem=8G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%A_%a.out
#SBATCH --signal=B:USR1@300
#SBATCH --requeue
set -euo pipefail
JOBFILE=${1:?job file}
LINE=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$JOBFILE")
echo "[$(date)] task ${SLURM_ARRAY_TASK_ID}: ${LINE}"

# Requeue before the wall-clock limit; training resumes from checkpoints/latest.pt (FR-INF-03).
trap 'echo "[$(date)] time limit near, requeueing"; scontrol requeue ${SLURM_JOB_ID}; exit 0' USR1

# Python environment. By default the job uses the environment it was submitted from
# (sbatch exports the submitting shell's PATH). Optional overrides:
#   RADSEARCH_MODULE=anaconda3/2024.06   module to load first
#   RADSEARCH_ENV=radsearch              conda env to activate
if [ -n "${RADSEARCH_MODULE:-}" ]; then module load "${RADSEARCH_MODULE}"; fi
if [ -n "${RADSEARCH_ENV:-}" ]; then
  source "${CONDA_PREFIX:-$HOME/miniconda3}/etc/profile.d/conda.sh" 2>/dev/null || true
  conda activate "${RADSEARCH_ENV}"
fi
echo "python: $(command -v python)"
python -c "import radsearch, torch, numba; print('torch', torch.__version__, '| numba', numba.__version__)" \
  || { echo "radsearch is not importable in this environment - check the module/conda env"; exit 1; }
export NUMBA_NUM_THREADS=${SLURM_CPUS_PER_TASK} OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export WANDB_MODE=${WANDB_MODE:-offline}

# NFR-02: unit tests gate every batch (fast, ~15 s); skip with SKIP_TESTS=1
if [ "${SKIP_TESTS:-0}" != "1" ] && [ "${SLURM_ARRAY_TASK_ID}" = "1" ]; then
  python -m pytest -q tests || { echo "tests failed - aborting batch"; scancel "${SLURM_ARRAY_JOB_ID}"; exit 1; }
fi

python -m radsearch.train ${LINE} &
wait $!
