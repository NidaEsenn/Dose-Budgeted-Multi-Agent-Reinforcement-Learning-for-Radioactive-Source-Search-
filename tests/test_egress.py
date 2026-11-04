"""D21: safe-exit rule and the predicted-dose observation."""
import numpy as np
import pytest

from radsearch.env import EnvConfig, RadSearchCore, exit_costs
from radsearch.world import bfs_distances


def test_exit_cost_counts_cells_entered_on_shortest_route():
    occ = np.zeros((5, 4), bool)
    D = bfs_distances(occ, (0, 0))[None]
    step = np.ones((1, 5, 4))
    c = exit_costs(step, D)[0]
    assert c[0, 0] == 0
    np.testing.assert_allclose(c, D[0].astype(float))      # one unit per cell entered


def test_exit_cost_prefers_low_dose_among_shortest_routes():
    occ = np.zeros((3, 3), bool)
    D = bfs_distances(occ, (0, 0))[None]
    step = np.ones((1, 3, 3)); step[0, 1, 0] = 100.0        # hot cell on one of the two routes
    c = exit_costs(step, D)[0]
    assert c[1, 1] == pytest.approx(2.0)                    # goes via (0,1), not (1,0)


def _core(**kw):
    base = dict(n_particles=300, max_steps=3, n_agents=2, n_obstacles=0, terminate_on_confident=False,
                shuffle_budgets=False)
    base.update(kw)
    c = RadSearchCore(EnvConfig(**base), 1, autoreset=False)
    c.reset_env(0, seed=3)
    return c


def test_robot_without_exit_budget_is_stranded():
    c = _core(budget_base_Gy=1.0)
    door = c.layouts[0].door
    far = np.argwhere(c.door_dist[0] == c.door_dist[0].max())[0]
    c.cells[0] = [door, far]
    c.budget[0] = [1.0, c.exit_true[0, far[0], far[1]] * 0.5]   # robot 1 can't afford the way out
    for _ in range(3):
        out = c.step(np.full((1, 2), 4))
    ep = out["episodes"][0]
    assert ep["stranded"] == [False, True] and ep["any_violation"]
    assert out["cost_violation"][0, 1] == 1.0
    assert ep["exit_dose"][0] == pytest.approx(0.0)


def test_egress_can_be_switched_off():
    c = _core(budget_base_Gy=1e-12, egress_required=False)
    c.budget[0] = 1.0
    for _ in range(3):
        out = c.step(np.full((1, 2), 4))
    assert not out["episodes"][0]["any_stranded"]


def test_estimated_exit_matches_truth_when_estimate_is_exact():
    c = _core()
    c.pf.x[0, :, :2] = c.src[0]; c.pf.x[0, :, 2] = c.logA[0]; c.pf._cache = None
    _, ex = c.estimated_fields()
    free = c.door_dist[0] >= 0
    np.testing.assert_allclose(ex[0][free], c.exit_true[0][free], rtol=1e-9)


def test_observation_layout_flag():
    on, off = _core(), _core(obs_predicted_dose=False)
    assert on.obs_dim == off.obs_dim + 6
    o1, _ = on.observe(); o0, _ = on.observe(with_pred=False)
    assert o1.shape[-1] == on.obs_dim and o0.shape[-1] == off.obs_dim
    assert np.isfinite(o1).all() and (o1[..., -6:] >= 0).all() and (o1[..., -6:] <= 1).all()


def test_old_checkpoint_runs_in_new_environment():
    from radsearch.algos.policy import load_policy
    pol = load_policy("models/mappo_sanity_0.1Gy.pt")
    assert pol.with_pred is False
    c = _core(n_agents=4)
    a = pol.act(c)
    assert a.shape == (1, 4)
