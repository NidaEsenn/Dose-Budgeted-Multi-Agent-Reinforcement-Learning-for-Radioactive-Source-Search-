import numpy as np
import pytest

from radsearch.baselines import make_baseline
from radsearch.env import EnvConfig, RadSearchCore
from radsearch.shield import DoseShield


@pytest.mark.parametrize("name", ["random", "approach", "perimeter", "greedy", "shielded_greedy"])
def test_baseline_runs(name):
    core = RadSearchCore(EnvConfig(n_particles=300, max_steps=20), 2)
    core.reset_all(seeds=[0, 1])
    pol = make_baseline(name)
    for _ in range(20):
        a = pol.act(core)
        assert a.shape == (2, 4) and ((a >= 0) & (a < 5)).all()
        core.step(a)


@pytest.mark.parametrize("name", ["approach", "perimeter", "greedy", "shielded_greedy"])
def test_baselines_do_not_read_truth(name):
    """Actions must not change when the true source is moved (deployability)."""
    acts = []
    for fake in (None, np.array([1.5, 1.5])):
        core = RadSearchCore(EnvConfig(n_particles=300), 1, autoreset=False)
        core.reset_env(0, seed=4)
        if fake is not None:
            core.src[0] = fake; core.logA[0] = 13.9
        acts.append(make_baseline(name).act(core))
    np.testing.assert_array_equal(acts[0], acts[1])


def test_shield_blocks_over_budget_moves():
    core = RadSearchCore(EnvConfig(n_particles=500, n_obstacles=0), 1, autoreset=False)
    core.reset_env(0, seed=0)
    core.pf.x[0, :, :2] = core.robot_xy()[0, 0] + np.array([0.0, 1.0])  # posterior: source just above robot 0
    core.pf.x[0, :, 2] = 14.0
    core.pf._cache = None
    core.dose[0, 0] = core.budget[0, 0] * 0.999
    m = DoseShield().mask(core)
    assert m[0, 0].sum() >= 1
    assert not m[0, 0, 0]  # moving onto the predicted source is blocked
