"""Watch a mission in the 3-D MuJoCo world: saves a GIF and a still image.

    python scripts/demo3d.py --policy models/mappo_sanity_0.1Gy.pt --seed 44
    python scripts/demo3d.py --policy baseline:perimeter --seed 3 --out perimeter3d.gif

The floor shows the true dose rate (log colour scale), grey blocks are
concrete obstacles, the green ball is the source, and each coloured robot
carries its detector on a mast at 0.3 m.
On a desktop, add --viewer to watch interactively in MuJoCo's own window.
"""
import argparse
import os
import sys

# Headless Linux (servers, clusters) has no display: render off-screen with OSMesa.
# Only this rendering script sets it -- with MUJOCO_GL=osmesa set, PyTorch's
# optimizer crashes, so never export it globally or in a training job.
if sys.platform.startswith("linux") and not os.environ.get("DISPLAY") and "--viewer" not in sys.argv:
    os.environ.setdefault("MUJOCO_GL", "osmesa")

import numpy as np  # noqa: E402

from radsearch.eval.runner import TEST_SEED_BASE
from radsearch.evaluate import load_env_cfg, make_policy

ap = argparse.ArgumentParser()
ap.add_argument("--policy", default="baseline:perimeter")
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--set", nargs="*", default=["budget_base_Gy=0.1"])
ap.add_argument("--out", default="demo3d.gif")
ap.add_argument("--fps", type=int, default=10)
ap.add_argument("--frame_every", type=float, default=1.0, help="simulated seconds between frames")
ap.add_argument("--viewer", action="store_true", help="interactive MuJoCo window (desktop only)")
a = ap.parse_args()

cfg = load_env_cfg(None, a.set)
policy = make_policy(a.policy)

if a.viewer:
    import time
    import mujoco.viewer
    from radsearch.env import RadSearchCore
    from radsearch.sim3d.mujoco_world import MujocoWorld
    core = RadSearchCore(cfg, 1, autoreset=False)
    core.reset_env(0, seed=TEST_SEED_BASE + a.seed)
    policy.reset(core, 0) if hasattr(policy, "reset") else None
    world = MujocoWorld(core)
    with mujoco.viewer.launch_passive(world.model, world.data) as v:
        for t in range(cfg.max_steps):
            act = policy.act(core)
            tg = world.targets_from_actions(act[0])
            for _ in range(int(cfg.step_time / world.model.opt.timestep / 10)):
                world.drive(tg, 10 * world.model.opt.timestep)
                v.sync(); time.sleep(0.01)
            out = core.step(act, xy_override=world.positions()[None])
            if out["done"][0] or not v.is_running():
                break
        print(out["episodes"][0] if out["done"][0] else "stopped")
        time.sleep(3)
    raise SystemExit

from radsearch.sim3d.runner import run_mission_3d
res = run_mission_3d(policy, cfg, TEST_SEED_BASE + a.seed, render=True, frame_every=a.frame_every)
ep = res["episode"]
from PIL import Image
imgs = [Image.fromarray(f) for f in res["frames"]]
imgs[0].save(a.out, save_all=True, append_images=imgs[1:], duration=int(1000 / a.fps), loop=0)
still = os.path.splitext(a.out)[0] + "_final.png"
imgs[-1].save(still)
err = max(l["track_error"] for l in res["log"])
print(f"source {ep['activity_TBq']:.1f} TBq, estimate error {ep['error']:.2f} m -> "
      f"{'SUCCESS' if ep['success'] else 'FAILED'} in {ep['steps']} steps; max tracking error {err:.2f} m")
for i, (d, b, v) in enumerate(zip(ep["dose"], ep["budget"], ep["violated"])):
    print(f"  robot {i}: dose {d:.3f} / {b:.3f} Gy" + ("  OVER BUDGET (retired)" if v else ""))
print("saved", a.out, "and", still)
