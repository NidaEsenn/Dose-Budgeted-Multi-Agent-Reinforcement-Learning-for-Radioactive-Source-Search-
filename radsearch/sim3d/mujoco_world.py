"""3-D MuJoCo world for the source-search task (FR-ENV-11 direction).

Design (docs/DESIGN_DECISIONS.md, D20): MuJoCo simulates only the robots'
*motion* -- rigid-body dynamics, motor limits and collisions with walls,
obstacles and each other. Radiation, dose and the particle filter stay in
:mod:`radsearch.physics` / :class:`radsearch.env.RadSearchCore`, evaluated
at the robots' real continuous positions. One physics model, no drift
between a 2-D and a 3-D copy.

Every 10-s decision step the high-level policy (trained grid policy or a
baseline) picks a neighbouring cell; a proportional velocity controller
drives each robot's base toward that cell's centre for the step duration.
"""
from __future__ import annotations

import os
import tempfile

import numpy as np

try:
    import mujoco
except ImportError as e:  # pragma: no cover
    raise ImportError("pip install mujoco  (or pip install -e '.[sim3d]')") from e

from ..world import MOVES

ROBOT_COLORS = [(0.12, 0.47, 0.71), (1.0, 0.50, 0.05), (0.17, 0.63, 0.17), (0.84, 0.15, 0.16),
                (0.58, 0.40, 0.74), (0.55, 0.34, 0.29)]
WALL_H = 1.5          # obstacle / wall height [m] (taller than the 0.3 m detector)
BASE_R = 0.25         # robot base radius [m]
BASE_H = 0.18
MAST_TOP = 0.30       # detector height, matches physics_constants.yaml detector.height_m


def _floor_texture(core, b: int, path: str, res: float = 0.1):
    """Write the true dose-rate field as a PNG (log colour scale) for the floor."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import cm
    from matplotlib.colors import LogNorm
    from PIL import Image
    from ..render import dose_rate_map
    _, _, rate = dose_rate_map(core, b, res)              # (nx, ny), x-major
    rate = np.where(core.occ[b].repeat(int(1 / res), 0).repeat(int(1 / res), 1), np.nan, rate)
    vmax = np.nanmax(rate)
    norm = LogNorm(vmin=vmax * 1e-5, vmax=vmax, clip=True)
    rgba = cm.magma(norm(np.nan_to_num(rate, nan=np.nanmin(rate))))
    img = (rgba[..., :3] * 255).astype(np.uint8)
    # image rows run top->bottom = +y->-y; columns = +x
    img = np.flipud(img.transpose(1, 0, 2))
    Image.fromarray(img).save(path)


def build_mjcf(core, b: int = 0, texture_path: str | None = None, show_source: bool = True) -> str:
    cfg = core.cfg
    W, H = cfg.width * cfg.cell, cfg.height * cfg.cell
    lay = core.layouts[b]
    tex = (f'<texture name="dose" type="2d" file="{texture_path}"/>'
           f'<material name="floor" texture="dose" texrepeat="1 1" texuniform="false"/>'
           if texture_path else '<material name="floor" rgba="0.85 0.86 0.86 1"/>')
    parts = [f'''<mujoco model="radsearch">
  <compiler angle="radian"/>
  <option timestep="0.01" gravity="0 0 -9.81"/>
  <visual><global offwidth="1920" offheight="1200"/><quality shadowsize="4096"/>
    <headlight ambient="0.45 0.45 0.45" diffuse="0.5 0.5 0.5"/></visual>
  <asset>{tex}
    <material name="concrete" rgba="0.62 0.64 0.65 1"/>
    <material name="wall" rgba="0.78 0.80 0.80 0.35"/>
  </asset>
  <worldbody>
    <light pos="{W/2} {H/2} 18" dir="0 0 -1" diffuse="0.6 0.6 0.6" castshadow="true"/>
    <geom name="floor" type="plane" pos="{W/2} {H/2} 0" size="{W/2} {H/2} 0.1" material="floor"/>''']
    t = 0.1
    for name, (cx, cy, sx, sy) in dict(
            wall_s=(W / 2, -t, W / 2 + t, t), wall_n=(W / 2, H + t, W / 2 + t, t),
            wall_w=(-t, H / 2, t, H / 2), wall_e=(W + t, H / 2, t, H / 2)).items():
        parts.append(f'    <geom name="{name}" type="box" pos="{cx} {cy} {WALL_H/2}" '
                     f'size="{sx} {sy} {WALL_H/2}" material="wall"/>')
    for k, (x0, y0, x1, y1) in enumerate(lay.rects):
        parts.append(f'    <geom name="obstacle_{k}" type="box" pos="{(x0+x1)/2} {(y0+y1)/2} {WALL_H/2}" '
                     f'size="{(x1-x0)/2} {(y1-y0)/2} {WALL_H/2}" material="concrete"/>')
    if show_source:
        sx, sy = core.src[b]
        parts.append(f'    <geom name="source" type="sphere" pos="{sx} {sy} 0.08" size="0.08" '
                     f'rgba="0.2 1 0.3 1" contype="0" conaffinity="0" group="2"/>')
    xy0 = core.robot_xy()[b]
    for i in range(core.N):
        r, g, bl = ROBOT_COLORS[i % len(ROBOT_COLORS)]
        parts.append(f'''    <body name="robot_{i}" pos="{xy0[i,0]} {xy0[i,1]} {BASE_H/2 + 0.01}">
      <joint name="r{i}_x" type="slide" axis="1 0 0" damping="1"/>
      <joint name="r{i}_y" type="slide" axis="0 1 0" damping="1"/>
      <geom name="r{i}_base" type="cylinder" size="{BASE_R} {BASE_H/2}" mass="8" rgba="{r} {g} {bl} 1" friction="0.2" group="2"/>
      <geom name="r{i}_mast" type="cylinder" fromto="0 0 {BASE_H/2} 0 0 {MAST_TOP - BASE_H/2 - 0.01}" size="0.03" rgba="0.15 0.15 0.15 1" contype="0" conaffinity="0" group="2"/>
      <geom name="r{i}_detector" type="sphere" pos="0 0 {MAST_TOP - BASE_H/2 - 0.01}" size="0.05" rgba="0.95 0.95 0.95 1" contype="0" conaffinity="0" group="2"/>
      <site name="r{i}_detector_site" pos="0 0 {MAST_TOP - BASE_H/2 - 0.01}" size="0.01"/>
    </body>''')
    parts.append('  </worldbody>\n  <actuator>')
    for i in range(core.N):
        for ax in "xy":
            parts.append(f'    <velocity name="r{i}_v{ax}" joint="r{i}_{ax}" kv="80" ctrlrange="-0.6 0.6" ctrllimited="true"/>')
    parts.append('  </actuator>\n</mujoco>')
    return "\n".join(parts)


class MujocoWorld:
    """Physical motion layer for one environment slot of a RadSearchCore."""

    def __init__(self, core, b: int = 0, v_max: float = 0.5, kp: float = 1.5, texture: bool = True,
                 show_source: bool = True):
        self.core, self.b, self.v_max, self.kp = core, b, v_max, kp
        self._tmp = tempfile.mkdtemp(prefix="radsearch3d_")
        tex = None
        if texture:
            tex = os.path.join(self._tmp, "dose.png")
            _floor_texture(core, b, tex)
        self.xml = build_mjcf(core, b, tex, show_source)
        self.model = mujoco.MjModel.from_xml_string(self.xml)
        self.data = mujoco.MjData(self.model)
        self.qx = [self.model.joint(f"r{i}_x").qposadr[0] for i in range(core.N)]
        self.qy = [self.model.joint(f"r{i}_y").qposadr[0] for i in range(core.N)]
        self.body0 = np.array([self.model.body(f"robot_{i}").pos[:2] for i in range(core.N)])
        mujoco.mj_forward(self.model, self.data)

    def positions(self) -> np.ndarray:
        q = self.data.qpos
        return self.body0 + np.stack([[q[self.qx[i]], q[self.qy[i]]] for i in range(self.core.N)])

    def targets_from_actions(self, actions: np.ndarray) -> np.ndarray:
        """Centre of the neighbouring cell each robot is asked to move to."""
        c = self.core
        cell = c.cfg.cell
        cur = np.floor(self.positions() / cell).astype(int)
        nxt = cur + MOVES[np.asarray(actions)]
        tgt = []
        for i in range(c.N):
            x, y = nxt[i]
            ok = 0 <= x < c.cfg.width and 0 <= y < c.cfg.height and not c.occ[self.b, x, y]
            if not c.active[self.b, i] or not ok:
                x, y = cur[i]
            tgt.append(((x + 0.5) * cell, (y + 0.5) * cell))
        return np.array(tgt)

    def drive(self, targets: np.ndarray, duration: float, frame_every: float | None = None,
              renderer=None, camera=None):
        """Run physics for ``duration`` s, steering each active robot to its target."""
        m, d = self.model, self.data
        n = int(round(duration / m.opt.timestep))
        k_frame = None if not frame_every else max(1, int(round(frame_every / m.opt.timestep)))
        frames = []
        active = self.core.active[self.b]
        for s in range(n):
            err = targets - self.positions()
            v = np.clip(self.kp * err, -self.v_max, self.v_max)
            v[~active] = 0.0
            d.ctrl[:] = v.reshape(-1)
            mujoco.mj_step(m, d)
            if renderer is not None and k_frame and s % k_frame == 0:
                renderer.update_scene(d, camera=camera)
                frames.append(renderer.render().copy())
        return frames

    def line_of_sight_blocked(self, p0, p1, z: float = MAST_TOP) -> bool:
        """MuJoCo ray cast between two points at detector height (validation helper)."""
        a = np.array([p0[0], p0[1], z], float)
        vec = np.array([p1[0] - p0[0], p1[1] - p0[1], 0.0])
        L = np.linalg.norm(vec)
        if L == 0:
            return False
        geomid = np.zeros(1, np.int32)
        groups = np.array([1, 1, 0, 1, 1, 1], np.uint8)  # group 2 = robots, source marker
        dist = mujoco.mj_ray(self.model, self.data, a, vec / L, groups, 1, -1, geomid)
        if dist < 0 or dist > L:
            return False
        name = mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_GEOM, int(geomid[0])) or ""
        return name.startswith("obstacle_")


def default_camera(core, b=0, azimuth=225.0, elevation=-50.0, distance=27.0):
    cam = mujoco.MjvCamera()
    cfg = core.cfg
    cam.lookat[:] = [cfg.width * cfg.cell / 2, cfg.height * cfg.cell / 2, 0.0]
    cam.distance, cam.azimuth, cam.elevation = distance, azimuth, elevation
    return cam
