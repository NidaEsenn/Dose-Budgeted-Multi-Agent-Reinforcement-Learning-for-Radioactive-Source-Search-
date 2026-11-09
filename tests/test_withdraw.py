"""K0.1 withdraw action, K1.2 potential shaping, K1.3 wrong-declaration penalty."""
import os

import numpy as np
import pytest

from radsearch.env import EnvConfig, RadSearchCore
from radsearch.world import WITHDRAW


def _core(**kw):
    cfg = EnvConfig(n_agents=3, n_particles=300, **kw)
    core = RadSearchCore(cfg, n_envs=2, seed=1, autoreset=False)
    core.reset_all(seeds=[5, 6])
    return core


def test_withdraw_accrues_true_exit_dose_and_leaves():
    core = _core()
    assert core.n_actions == 6 and core.action_mask().shape[-1] == 6
    for _ in range(3):                                   # walk a bit into the room
        core.step(np.zeros((2, 3), int))
    b, i = 0, 1
    cell = core.cells[b, i].copy()
    exit_true = core.exit_true[b, cell[0], cell[1]]
    dose0 = core.dose[b, i]
    act = np.full((2, 3), 4); act[b, i] = WITHDRAW
    out = core.step(act)
    assert core.withdrawn[b, i] and not core.active[b, i]
    assert np.isclose(core.dose[b, i], dose0 + exit_true)
    assert np.isclose(out["cost_dose"][b, i], exit_true / core.budget[b, i])
    assert out["in_mission"][b, i] and not out["term_agent"][b, i]
    # later: no dose, no measurement, only 'stay' allowed, still in the mission
    d1 = core.dose[b, i]
    out = core.step(np.zeros((2, 3), int))
    assert core.dose[b, i] == d1
    m = core.action_mask()[b, i]
    assert m[4] and m.sum() == 1
    assert out["in_mission"][b, i] and not out["acting"][b, i]


def test_withdraw_over_budget_is_stranded_violation():
    core = _core()
    core.step(np.zeros((2, 3), int))
    b, i = 1, 0
    ex = core.exit_true[b, core.cells[b, i, 0], core.cells[b, i, 1]]
    core.budget[b, i] = core.dose[b, i] + 0.5 * max(ex, 1e-12)
    act = np.full((2, 3), 4); act[b, i] = WITHDRAW
    out = core.step(act)
    if ex > 0:
        assert core.violated[b, i] and core.stranded[b, i]
        assert out["cost_violation"][b, i] == 1 and out["term_agent"][b, i]


def test_all_withdrawn_ends_episode():
    core = _core()
    out = core.step(np.full((2, 3), WITHDRAW))
    assert out["done"].all()
    assert all(all(e["withdrawn"]) for e in out["episodes"])


def test_potential_shaping_telescopes():
    """Sum_t gamma^t F_t = -Phi(s_0) whatever the trajectory (Phi(terminal) = 0)."""
    g = 0.99
    core = _core(shaping_gamma=g, time_penalty=0.0, success_bonus=0.0, wrong_declare_penalty=0.0,
                 max_steps=12, terminate_on_confident=False)
    phi0 = core.phi.copy()
    rng = np.random.default_rng(0)
    tot = np.zeros(2); disc = np.ones(2); live = np.ones(2, bool)
    while live.any():
        out = core.step(rng.integers(5, size=(2, 3)))
        tot += np.where(live, disc * out["reward"], 0.0)
        disc *= g
        live &= ~out["done"]
        core.t[~live] = 0; core.active[~live] = False
    assert np.allclose(tot, -phi0, atol=1e-9)


def test_wrong_declaration_penalised():
    core = _core(confident_sigma=1e9, min_steps=1, shaping="diff", time_penalty=0.0)
    core.err[:] = 0  # irrelevant for 'diff' delta sign; we only check the terminal term
    out = core.step(np.full((2, 3), 4))
    for b, e in enumerate(out["episodes"]):
        assert e["confident"]
        shaped = out["reward"][b]
        if e["wrong_declare"]:
            assert shaped < 0.5   # -1 penalty dominates the shaping delta (|delta| << 1)
        assert e["wrong_declare"] == (not e["success"])


def test_reserve_withdraw_wrapper_runs():
    from radsearch.baselines import make_baseline
    core = _core()
    for spec in ("approach+withdraw", "approach+withdraw_mean"):
        pol = make_baseline(spec, wd_margin=0.9)
        a = pol.act(core)
        assert a.shape == (2, 3) and a.max() <= WITHDRAW


@pytest.mark.skipif(not os.path.exists("models/mappo_sanity_0.1Gy.pt"), reason="no checkpoint")
def test_old_five_action_checkpoint_runs_in_withdraw_env():
    from radsearch.algos.policy import load_policy
    pol = load_policy("models/mappo_sanity_0.1Gy.pt")
    core = _core()
    a = pol.act(core)
    assert a.max() < WITHDRAW
