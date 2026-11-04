import numpy as np
import pytest

from radsearch.algos.mappo import AlgoConfig, Lagrange, MAPPOTrainer
from radsearch.algos.policy import load_policy
from radsearch.env import EnvConfig
from radsearch.eval.runner import run_episodes


def test_lagrange_gd_matches_safe_policy_optimization_rule():
    """FR-ALG-06: lambda <- max(0, lambda + lr * (Jc - d)), per robot."""
    L = Lagrange(3, AlgoConfig(lambda_lr=0.1, cost_version="A"))
    L.update(np.array([1.0, 0.5, 0.75]), np.ones(3, bool))
    np.testing.assert_allclose(L.lam, [0.025, 0.0, 0.0])
    L.update(np.array([0.0, 0.0, 2.0]), np.array([True, True, False]))
    np.testing.assert_allclose(L.lam, [0.0, 0.0, 0.0])  # invalid robot untouched


def test_lagrange_shared():
    L = Lagrange(3, AlgoConfig(lambda_lr=1.0, lambda_sharing="shared"))
    L.update(np.array([1.75, 0.75, 0.75]), np.ones(3, bool))
    np.testing.assert_allclose(L.lam, [1 / 3] * 3)


def test_lagrange_pid_nonnegative():
    L = Lagrange(2, AlgoConfig(lambda_mode="pid"))
    for j in ([2.0, 0.0], [2.0, 0.0]):
        L.update(np.array(j), np.ones(2, bool))
        assert (L.lam >= 0).all()
    assert L.lam[0] > 0 and L.lam[1] == 0
    L.update(np.array([0.0, 0.0]), np.ones(2, bool))   # below limit -> proportional term releases
    assert (L.lam >= 0).all() and L.integral[0] > 0


@pytest.mark.parametrize("method,version,shield", [("mappo", "A", False), ("mappo_lag", "A", False),
                                                    ("mappo_lag", "B", True), ("mappo_penalty", "A", False)])
def test_train_resume_and_eval(tmp_path, method, version, shield):
    ecfg = EnvConfig(n_particles=200, max_steps=40)
    acfg = AlgoConfig(method=method, cost_version=version, shield=shield, n_envs=4, rollout_len=16,
                      total_env_steps=4 * 16 * 2, run_dir=str(tmp_path), checkpoint_every=1,
                      penalty_beta=0.1)
    MAPPOTrainer(ecfg, acfg).train()
    acfg.total_env_steps = 4 * 16 * 3
    tr = MAPPOTrainer(ecfg, acfg)
    assert tr.env_steps == 4 * 16 * 2          # FR-INF-03 automatic resume
    tr.train()
    pol = load_policy(str(tmp_path / "checkpoints" / "final.pt"))
    eps = run_episodes(pol, ecfg, [1, 2])
    assert len(eps) == 2 and all(e is not None for e in eps)


def test_version_b_team_chance_split():
    """Per-robot limit d/N bounds P(any robot violates) by d (union bound)."""
    cfg = AlgoConfig(cost_version="B", cost_limit=0.05)
    assert cfg.limit(4) == pytest.approx(0.0125)
    assert AlgoConfig(cost_version="B", team_chance_split=False).limit(4) == pytest.approx(0.05)
    assert AlgoConfig(cost_version="A").limit(4) == pytest.approx(0.75)


def test_version_b_lambda_uses_violations_not_dose_shaping(tmp_path):
    """With kappa > 0 and no violations, lambda must not grow (D22)."""
    ecfg = EnvConfig(n_particles=200, max_steps=20, budget_base_Gy=100.0)   # budgets never bind
    acfg = AlgoConfig(method="mappo_lag", cost_version="B", cost_kappa=1.0, lambda_lr=1.0,
                      n_envs=4, rollout_len=32, total_env_steps=4 * 32 * 3, run_dir=str(tmp_path))
    tr = MAPPOTrainer(ecfg, acfg).train()
    assert np.allclose(tr.lagr.lam, 0.0)
