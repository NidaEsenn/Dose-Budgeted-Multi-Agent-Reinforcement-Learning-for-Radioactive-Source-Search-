"""Run a mission with any policy, with robot motion simulated in MuJoCo.

The policy sees exactly the observation it was trained on; the only change is
that robots now *physically* drive between cells (finite speed, collisions,
imperfect stopping), and radiation is measured at their real positions.
"""
from __future__ import annotations

import numpy as np

from ..env import RadSearchCore
from .mujoco_world import MujocoWorld, default_camera


def run_mission_3d(policy, cfg, seed: int, render: bool = False, width: int = 960, height: int = 720,
                   frame_every: float = 1.0, max_steps: int | None = None, v_max: float = 0.5):
    core = RadSearchCore(cfg, 1, autoreset=False)
    core.reset_env(0, seed=seed)
    if hasattr(policy, "reset"):
        policy.reset(core, 0)
    world = MujocoWorld(core, 0, v_max=v_max)
    renderer = cam = None
    frames = []
    if render:
        import mujoco
        renderer = mujoco.Renderer(world.model, height, width)
        cam = default_camera(core)
    log = []
    steps = max_steps or cfg.max_steps
    for t in range(steps):
        actions = policy.act(core)
        targets = world.targets_from_actions(actions[0])
        frames += world.drive(targets, cfg.step_time, frame_every if render else None, renderer, cam)
        xy = world.positions()
        out = core.step(actions, xy_override=xy[None])
        log.append(dict(t=t + 1, xy=xy.tolist(), target=targets.tolist(),
                        track_error=float(np.linalg.norm(xy - targets, axis=1).max()),
                        dose=core.dose[0].tolist(), active=core.active[0].tolist()))
        if out["done"][0]:
            ep = out["episodes"][0]
            break
    else:
        ep = core.episode_info(0)
    if renderer is not None:
        renderer.update_scene(world.data, camera=cam)
        frames.append(renderer.render().copy())
    return dict(episode=ep, log=log, frames=frames, world=world)
