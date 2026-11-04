import numpy as np
import pytest

mujoco = pytest.importorskip("mujoco")

from radsearch import physics as P  # noqa: E402
from radsearch.baselines import make_baseline  # noqa: E402
from radsearch.env import EnvConfig, RadSearchCore  # noqa: E402
from radsearch.sim3d.mujoco_world import BASE_R, MujocoWorld  # noqa: E402
from radsearch.sim3d.runner import run_mission_3d  # noqa: E402


def make_world(seed=5, **kw):
    cfg = EnvConfig(n_particles=200, max_steps=15, **kw)
    core = RadSearchCore(cfg, 1, autoreset=False)
    core.reset_env(0, seed=seed)
    return core, MujocoWorld(core, texture=False)


def test_mujoco_ray_agrees_with_attenuation_geometry():
    """MuJoCo's ray cast and our slab clipping agree on which paths cross an obstacle."""
    core, w = make_world(seed=11)
    rects = core.layouts[0].rects
    assert len(rects) > 0
    rng = np.random.default_rng(0)
    checked = 0
    for _ in range(400):
        p0, p1 = rng.uniform(0.3, 19.7, 2), rng.uniform(0.3, 19.7, 2)
        if core.occ[0][tuple(np.floor(p0).astype(int))] or core.occ[0][tuple(np.floor(p1).astype(int))]:
            continue
        chord = P.rect_chord_lengths(p0, p1, rects).sum()
        if 0 < chord < 0.02:      # grazing a corner: ambiguous within float tolerance
            continue
        assert w.line_of_sight_blocked(p0, p1) == (chord > 0)
        checked += 1
    assert checked > 200


def test_robot_reaches_next_cell_in_one_step():
    core, w = make_world()
    tgt = w.targets_from_actions(np.full(core.N, 4))           # stay
    tgt[0] = w.targets_from_actions(np.array([0] + [4] * (core.N - 1)))[0]  # robot 0 moves up
    w.drive(tgt, core.cfg.step_time)
    assert np.linalg.norm(w.positions()[0] - tgt[0]) < 0.05


def test_robots_collide_instead_of_overlapping():
    core, w = make_world()
    tgt = np.repeat(w.positions()[:1], core.N, axis=0)          # everyone to robot 0's spot
    w.drive(tgt, core.cfg.step_time)
    xy = w.positions()
    d = np.linalg.norm(xy[:, None] - xy[None], axis=-1) + np.eye(core.N) * 10
    assert d.min() > 2 * BASE_R - 0.05


def test_3d_mission_matches_2d_when_motion_is_perfect():
    """Same seed, same deterministic policy: 3-D motion reproduces the 2-D doses."""
    cfg = EnvConfig(n_particles=200, max_steps=12)
    pol2, pol3 = make_baseline("approach"), make_baseline("approach")
    core = RadSearchCore(cfg, 1, autoreset=False)
    core.reset_env(0, seed=10_000_044)
    doses2 = []
    for _ in range(cfg.max_steps):
        out = core.step(pol2.act(core))
        doses2.append(core.dose[0].copy())
        if out["done"][0]:
            break
    res = run_mission_3d(pol3, cfg, 10_000_044, max_steps=len(doses2))
    d3 = np.array(res["log"][-1]["dose"])
    np.testing.assert_allclose(d3, doses2[len(res["log"]) - 1], rtol=0.05, atol=1e-6)


def test_sdf_export_is_valid_xml_with_all_obstacles():
    import xml.etree.ElementTree as ET
    from radsearch.sim3d.sdf_export import layout_to_sdf
    core, _ = make_world(seed=11)
    root = ET.fromstring(layout_to_sdf(core))
    names = [m.get("name") for m in root.iter("model")]
    assert sum(n.startswith("obstacle_") for n in names) == len(core.layouts[0].rects)
    assert "radiation_source" in names and root.get("version") == "1.9"
