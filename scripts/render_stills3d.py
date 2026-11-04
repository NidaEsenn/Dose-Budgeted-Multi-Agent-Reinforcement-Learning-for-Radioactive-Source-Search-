"""High-resolution 3-D stills of one mission at chosen steps (for slides and posters).

    python scripts/render_stills3d.py --policy models/mappo_sanity_0.1Gy.pt --seed 72 --steps 0 18 21 --out docs/examples/stills

For each requested step it saves an overview and a close-up that follows the
robot closest to the source, plus a low "robot's-eye" view at the start.
"""
import argparse
import os
import sys

if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
    os.environ.setdefault("MUJOCO_GL", "osmesa")

import mujoco  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from radsearch.env import RadSearchCore  # noqa: E402
from radsearch.eval.runner import TEST_SEED_BASE  # noqa: E402
from radsearch.evaluate import load_env_cfg, make_policy  # noqa: E402
from radsearch.sim3d.mujoco_world import MujocoWorld  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--policy", default="models/mappo_sanity_0.1Gy.pt")
ap.add_argument("--seed", type=int, default=72)
ap.add_argument("--steps", type=int, nargs="+", default=[0, 18, 21])
ap.add_argument("--set", nargs="*", default=["budget_base_Gy=0.1"])
ap.add_argument("--out", default="docs/examples/stills")
ap.add_argument("--width", type=int, default=1600)
ap.add_argument("--height", type=int, default=1000)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)

cfg = load_env_cfg(None, a.set)
policy = make_policy(a.policy)
core = RadSearchCore(cfg, 1, autoreset=False)
core.reset_env(0, seed=TEST_SEED_BASE + a.seed)
world = MujocoWorld(core)
r = mujoco.Renderer(world.model, a.height, a.width)


def cam(lookat, distance, azimuth, elevation):
    c = mujoco.MjvCamera()
    c.lookat[:] = lookat
    c.distance, c.azimuth, c.elevation = distance, azimuth, elevation
    return c


def snap(name, c):
    r.update_scene(world.data, camera=c)
    Image.fromarray(r.render()).save(os.path.join(a.out, f"mission{a.seed}_{name}.png"))
    print("saved", name)


src = np.array([*core.src[0], 0.0])
centre = np.array([cfg.width / 2, cfg.height / 2, 0.0])
want = set(a.steps)
for t in range(cfg.max_steps + 1):
    if t in want:
        xy = world.positions()
        k = int(np.argmin(np.linalg.norm(xy - core.src[0], axis=1)))
        mid = np.array([*(0.5 * (xy[k] + core.src[0])), 0.2])
        snap(f"step{t:02d}_overview", cam(centre, 23, 215, -48))
        snap(f"step{t:02d}_closeup", cam(mid, 4.5, 215, -28))
        if t == 0:
            door = np.array([*xy.mean(0), 0.25])
            snap("step00_robots_eye", cam(door, 3.2, 200, -18))
    if t == max(want):
        break
    act = policy.act(core)
    world.drive(world.targets_from_actions(act[0]), cfg.step_time)
    out = core.step(act, xy_override=world.positions()[None])
    if out["done"][0]:
        print("mission ended at step", t + 1)
        if t + 1 in want:
            continue
        break
