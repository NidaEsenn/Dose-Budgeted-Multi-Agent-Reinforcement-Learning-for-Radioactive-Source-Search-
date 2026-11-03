import numpy as np
import pytest
from pettingzoo.test import parallel_api_test

from radsearch.env import EnvConfig, RadSearchCore
from radsearch.pz_env import RadSearchParallelEnv


def small_cfg(**kw):
    base = dict(n_particles=300, max_steps=30)
    base.update(kw)
    return EnvConfig(**base)


def test_parallel_api():  # FR-ENV-01 / AC-1
    env = RadSearchParallelEnv(small_cfg())
    parallel_api_test(env, num_cycles=40)


def test_seed_reproducible():  # FR-ENV-06 / NFR-01
    runs = []
    for _ in range(2):
        env = RadSearchParallelEnv(small_cfg())
        obs, _ = env.reset(seed=123)
        rng = np.random.default_rng(0)
        traj = []
        while env.agents:
            obs, r, *_ = env.step({a: int(rng.integers(5)) for a in env.agents})
            traj.append(sum(r.values()))
        runs.append((traj, env.core.dose.copy(), env.core.pf.estimate()[0].copy()))
    assert runs[0][0] == runs[1][0]
    np.testing.assert_array_equal(runs[0][1], runs[1][1])
    np.testing.assert_array_equal(runs[0][2], runs[1][2])


def test_batch_independent_of_composition():
    """Episode with seed s is identical whether it runs alone or in a batch."""
    cfg = small_cfg(terminate_on_confident=False)
    a = RadSearchCore(cfg, 1, autoreset=False); a.reset_env(0, seed=99)
    b = RadSearchCore(cfg, 3, autoreset=False); b.reset_all(seeds=[5, 99, 7])
    acts = np.random.default_rng(1).integers(5, size=(10, cfg.n_agents))
    for t in range(10):
        oa = a.step(acts[t][None])
        ob = b.step(np.stack([acts[t]] * 3))
        np.testing.assert_allclose(oa["obs"][0], ob["obs"][1])
        np.testing.assert_allclose(a.dose[0], b.dose[1])


def test_moves_into_obstacles_stay():  # FR-ENV-04
    core = RadSearchCore(small_cfg(n_agents=1), 1, autoreset=False)
    core.reset_env(0, seed=0)
    core.cells[0, 0] = [0, 0]
    core.step(np.array([[2]]))  # left into wall
    assert core.cells[0, 0].tolist() == [0, 0]
    core.occ[0, 0, 1] = True
    core.step(np.array([[0]]))  # up into obstacle
    assert core.cells[0, 0].tolist() == [0, 0]


def test_dose_accumulates_and_retirement():  # FR-PHY-02, FR-BUD-03/05
    cfg = small_cfg(n_agents=2, budget_base_Gy=1e-6, shuffle_budgets=False, n_obstacles=0,
                    terminate_on_confident=False)
    core = RadSearchCore(cfg, 1, autoreset=False)
    core.reset_env(0, seed=1)
    for _ in range(30):
        out = core.step(np.full((1, 2), 4))
        if out["done"][0]:
            break
    assert core.violated[0].all() and not core.active[0].any()
    ep = out["episodes"][0]
    assert ep["any_violation"] and all(s >= 0 for s in ep["violation_step"])
    frozen = core.dose.copy()
    assert core.action_mask()[0, :, :4].sum() == 0


def test_retired_robot_does_not_move():
    cfg = small_cfg(n_agents=2, budget_ratio=(1e-6, 1.0), shuffle_budgets=False, budget_base_Gy=0.5,
                    terminate_on_confident=False)
    core = RadSearchCore(cfg, 1, autoreset=False)
    core.reset_env(0, seed=2)
    core.step(np.array([[4, 4]]))
    assert not core.active[0, 0] and core.active[0, 1]
    pos = core.cells[0, 0].copy(); d = core.dose[0, 0]
    out = core.step(np.array([[0, 0]]))
    assert (core.cells[0, 0] == pos).all() and core.dose[0, 0] == d
    assert not out["acting"][0, 0]


def test_unequal_budgets_keep_mean():  # FR-BUD-02
    cfg = small_cfg(n_agents=3, budget_ratio=(1, 2, 4), budget_base_Gy=1.0)
    core = RadSearchCore(cfg, 1); core.reset_env(0, seed=3)
    b = np.sort(core.budget[0])
    np.testing.assert_allclose(b / b[0], [1, 2, 4]); assert b.mean() == pytest.approx(1.0)


def test_obs_shapes():
    for n in (3, 4, 6):
        core = RadSearchCore(small_cfg(n_agents=n), 2)
        obs, st = core.reset_all()
        assert obs.shape == (2, n, core.obs_dim) and st.shape == (2, n, core.state_dim)
        assert np.isfinite(obs).all() and np.isfinite(st).all()


def test_render():
    env = RadSearchParallelEnv(small_cfg(), render_mode="rgb_array")
    env.reset(seed=0)
    env.step({a: 0 for a in env.agents})
    img = env.render()
    assert img.ndim == 3 and img.shape[2] == 3


def test_free_run_lengths_reference():
    from radsearch.env import _free_run_lengths
    from radsearch.world import MOVES
    occ = np.random.default_rng(0).random((9, 7)) < 0.3
    ref = np.zeros((9, 7, 4))
    for a, (dx, dy) in enumerate(MOVES[:4]):
        for x in range(9):
            for y in range(7):
                n, cx, cy = 0, x + dx, y + dy
                while 0 <= cx < 9 and 0 <= cy < 7 and not occ[cx, cy]:
                    n += 1; cx += dx; cy += dy
                ref[x, y, a] = n
    np.testing.assert_array_equal(_free_run_lengths(occ), ref)
