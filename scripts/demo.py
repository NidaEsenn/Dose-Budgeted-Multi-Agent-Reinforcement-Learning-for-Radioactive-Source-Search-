"""Watch one mission: saves an animation (GIF) and the final frame (PNG).

    python scripts/demo.py                                    # perimeter baseline, seed 0
    python scripts/demo.py --policy models/mappo_sanity_0.1Gy.pt --seed 3
    python scripts/demo.py --policy baseline:approach --seed 3 --out approach.gif
    python scripts/demo.py --policy baseline:shielded_greedy --set activity_TBq=[30,100]

The picture shows the true dose-rate field (log colour scale), obstacles (grey),
the true source (green star), the team's current estimate (white x), the
particle cloud (cyan), and each robot's path with "dose / budget" in the legend.
A faded robot marker means the robot exceeded its budget and was retired.
"""
import argparse
import os

import numpy as np

from radsearch.env import RadSearchCore
from radsearch.evaluate import load_env_cfg, make_policy
from radsearch.eval.runner import TEST_SEED_BASE
from radsearch.render import render_frame, save_episode_animation

ap = argparse.ArgumentParser()
ap.add_argument("--policy", default="baseline:perimeter", help="model .pt path or baseline:<name>")
ap.add_argument("--seed", type=int, default=0, help="test mission number (same missions as the evaluation)")
ap.add_argument("--set", nargs="*", default=["budget_base_Gy=0.1"], help="env overrides, e.g. n_agents=6")
ap.add_argument("--out", default="demo.gif")
ap.add_argument("--fps", type=int, default=4)
ap.add_argument("--every", type=int, default=1, help="draw every k-th step (faster)")
a = ap.parse_args()

cfg = load_env_cfg(None, a.set)
policy = make_policy(a.policy)
core = RadSearchCore(cfg, 1, autoreset=False)
core.reset_env(0, seed=TEST_SEED_BASE + a.seed)
if hasattr(policy, "reset"):
    policy.reset(core, 0)
traj = [core.robot_xy()[0].copy()]
frames = [render_frame(core, 0, np.array(traj))]
t = 0
while True:
    out = core.step(policy.act(core))
    traj.append(core.robot_xy()[0].copy())
    t += 1
    if out["done"][0] or t % a.every == 0:
        frames.append(render_frame(core, 0, np.array(traj)))
    if out["done"][0]:
        ep = out["episodes"][0]
        break
save_episode_animation(frames, a.out, fps=a.fps)
png = os.path.splitext(a.out)[0] + "_final.png"
import matplotlib.pyplot as plt
plt.imsave(png, frames[-1])
print(f"source {ep['activity_TBq']:.1f} TBq at {np.round(ep['source'], 1).tolist()}, "
      f"estimate error {ep['error']:.2f} m -> {'SUCCESS' if ep['success'] else 'FAILED'} in {ep['steps']} steps")
for i, (d, b, v) in enumerate(zip(ep["dose"], ep["budget"], ep["violated"])):
    print(f"  robot {i}: dose {d:.3f} / {b:.3f} Gy" + ("  OVER BUDGET (retired)" if v else ""))
print(f"saved {a.out} and {png}")
