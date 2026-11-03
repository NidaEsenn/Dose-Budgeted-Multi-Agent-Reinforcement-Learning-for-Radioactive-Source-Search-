#!/bin/bash
# Evaluate every final checkpoint of an experiment on the test set + E5 generalisation.
#   sbatch --array=1-$(ls runs/E1/*/*/seed*/checkpoints/final.pt | wc -l) slurm/eval_array.sbatch E1
#SBATCH --job-name=radsearch-eval
#SBATCH --cpus-per-task=8
#SBATCH --mem=8G
#SBATCH --time=06:00:00
#SBATCH --output=logs/%x_%A_%a.out
set -euo pipefail
EXP=${1:?experiment}
CKPT=$(ls runs/${EXP}/*/*/seed*/checkpoints/final.pt | sed -n "${SLURM_ARRAY_TASK_ID}p")
RUN=$(dirname "$(dirname "$CKPT")")
ENVYAML="$RUN/hydra_config.yaml"
export NUMBA_NUM_THREADS=${SLURM_CPUS_PER_TASK}
python scripts/eval_run.py --run "$RUN" --grid
# E5: more robots (runs trained with n_agents < max_agents=6), out-of-range activity, unseen maps
python scripts/eval_run.py --run "$RUN" --tag more_robots --set n_agents=6 || true
python scripts/eval_run.py --run "$RUN" --tag high_activity --set "activity_TBq=[100.0,300.0]" "pf_logA_range=[12.0,14.5]"
python scripts/eval_run.py --run "$RUN" --tag dense_maps --set "n_obstacles=[7,10]" max_obstacle_size=5
