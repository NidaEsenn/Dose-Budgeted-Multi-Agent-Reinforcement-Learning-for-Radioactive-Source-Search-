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

source "${CONDA_PREFIX:-$HOME/miniconda3}/etc/profile.d/conda.sh" 2>/dev/null || true
conda activate radsearch 2>/dev/null || true
export NUMBA_NUM_THREADS=${SLURM_CPUS_PER_TASK} OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export WANDB_MODE=${WANDB_MODE:-offline}

# NFR-02: unit tests gate every batch (fast, ~15 s); skip with SKIP_TESTS=1
if [ "${SKIP_TESTS:-0}" != "1" ] && [ "${SLURM_ARRAY_TASK_ID}" = "1" ]; then
  python -m pytest -q tests || { echo "tests failed - aborting batch"; scancel "${SLURM_ARRAY_JOB_ID}"; exit 1; }
fi

python -m radsearch.train ${LINE} &
wait $!
