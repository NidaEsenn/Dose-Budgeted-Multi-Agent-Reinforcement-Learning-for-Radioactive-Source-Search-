"""Generate SLURM job-array files from the experiment matrix (Section 10).

Each line of ``slurm/jobs/<exp>.txt`` is one training run (Hydra overrides);
``slurm/train_array.sbatch`` runs line $SLURM_ARRAY_TASK_ID (FR-INF-02).

    python slurm/make_jobs.py            # writes slurm/jobs/E1.txt ... E4.txt
    sbatch --array=1-$(wc -l < slurm/jobs/E1.txt) slurm/train_array.sbatch slurm/jobs/E1.txt
"""
import itertools
import os

SEEDS = range(10)  # FR-EVAL-01
LIMITS = [0.1, 0.25, 0.4, 0.55, 0.75, 0.9, 1.0]       # MAPPO-L tuning points (E2)
BETAS = [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0]        # same number of penalty points (fairness rule)


def e1():
    for algo, n, s in itertools.product(["mappo", "mappo_lag_a", "mappo_lag_b", "mappo_lag_a_shield"],
                                        [3, 4, 6], SEEDS):
        yield f"experiment=E1 algo={algo} env.n_agents={n} env.name=n{n} seed={s}"


def e2():
    for d, s in itertools.product(LIMITS, SEEDS):
        yield f"experiment=E2 algo=mappo_lag_a algo.cost_limit={d} algo.name=mappo_lag_a_d{d} seed={s}"
    for b, s in itertools.product(BETAS, SEEDS):
        yield f"experiment=E2 algo=mappo_penalty algo.penalty_beta={b} seed={s}"
    for bud, s in itertools.product([0.1, 0.3, 1.0], SEEDS):
        yield f"experiment=E2 algo=mappo_lag_a env.budget_base_Gy={bud} env.name=budget{bud} seed={s}"


def e3():
    for env, s in itertools.product(["equal3", "unequal"], SEEDS):
        yield f"experiment=E3 algo=mappo_lag_a env={env} seed={s}"


def e4():
    for s in SEEDS:
        yield f"experiment=E4 algo=mappo_lag_a env=no_budget_obs seed={s}"
        yield f"experiment=E4 algo=mappo_lag_a_shared seed={s}"
        yield f"experiment=E4 algo=mappo_lag_a env=no_retire seed={s}"
        for m in (0.6, 0.8, 1.0):
            yield f"experiment=E4 algo=mappo_lag_a algo.cost_limit={m} algo.name=margin{m} seed={s}"


def p1():
    """Karar 3 pilot (D22-D24 rules, withdraw on): does a learned team beat the
    reference rule (greedy + withdraw, 84 % success / 4.3 % violations)?"""
    for algo, s in itertools.product(["mappo", "mappo_reserve", "mappo_lag_b"], range(3)):
        yield f"experiment=P1 algo={algo} seed={s}"


if __name__ == "__main__":
    os.makedirs("slurm/jobs", exist_ok=True)
    for name, gen in dict(P1=p1, E1=e1, E2=e2, E3=e3, E4=e4).items():
        lines = list(gen())
        with open(f"slurm/jobs/{name}.txt", "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"{name}: {len(lines)} jobs")
