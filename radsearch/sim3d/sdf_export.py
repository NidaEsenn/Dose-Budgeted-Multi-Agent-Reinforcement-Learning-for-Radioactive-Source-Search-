"""Export a room layout as a Gazebo (SDF 1.9) world, for ROS 2 / Gazebo Harmonic.

    python -m radsearch.sim3d.sdf_export --seed 10000072 --out mission72.sdf
    gz sim mission72.sdf          # on a machine with Gazebo installed

Walls and obstacles become static boxes; the source is a small visual-only
marker (named "radiation_source", position in the model pose) so a ROS 2
radiation-sensor node can read it. Robots are spawned separately (e.g. a
TurtleBot 4), see docs/ROS2_GAZEBO.md. Pure XML: needs no Gazebo to run.
"""
from __future__ import annotations

import argparse
from xml.sax.saxutils import escape

from ..env import EnvConfig, RadSearchCore
from .mujoco_world import WALL_H


def _box(name, x, y, sx, sy, h, rgba="0.62 0.64 0.65 1"):
    return f"""    <model name="{escape(name)}"><static>true</static>
      <pose>{x:.3f} {y:.3f} {h/2:.3f} 0 0 0</pose>
      <link name="link">
        <collision name="c"><geometry><box><size>{sx:.3f} {sy:.3f} {h:.3f}</size></box></geometry></collision>
        <visual name="v"><geometry><box><size>{sx:.3f} {sy:.3f} {h:.3f}</size></box></geometry>
          <material><ambient>{rgba}</ambient><diffuse>{rgba}</diffuse></material></visual>
      </link></model>"""


def layout_to_sdf(core, b: int = 0, with_source: bool = True) -> str:
    cfg = core.cfg
    W, H = cfg.width * cfg.cell, cfg.height * cfg.cell
    t = 0.2
    models = [_box("wall_south", W / 2, -t / 2, W + 2 * t, t, WALL_H, "0.8 0.8 0.8 1"),
              _box("wall_north", W / 2, H + t / 2, W + 2 * t, t, WALL_H, "0.8 0.8 0.8 1"),
              _box("wall_west", -t / 2, H / 2, t, H, WALL_H, "0.8 0.8 0.8 1"),
              _box("wall_east", W + t / 2, H / 2, t, H, WALL_H, "0.8 0.8 0.8 1")]
    for k, (x0, y0, x1, y1) in enumerate(core.layouts[b].rects):
        models.append(_box(f"obstacle_{k}", (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, WALL_H))
    if with_source:
        sx, sy = core.src[b]
        A = 10 ** core.logA[b] / 1e12
        models.append(f"""    <model name="radiation_source"><static>true</static>
      <!-- {escape(core.cfg.isotope)}, {A:.1f} TBq (simulated) -->
      <pose>{sx:.3f} {sy:.3f} 0.05 0 0 0</pose>
      <link name="link"><visual name="v"><geometry><sphere><radius>0.08</radius></sphere></geometry>
        <material><ambient>0.2 1 0.3 1</ambient><diffuse>0.2 1 0.3 1</diffuse></material></visual></link></model>""")
    starts = core.robot_xy()[b]
    spawn = "\n".join(f"    <!-- robot_{i} start: x={x:.2f} y={y:.2f} -->" for i, (x, y) in enumerate(starts))
    return f"""<?xml version="1.0"?>
<sdf version="1.9">
  <world name="radsearch">
    <physics name="1ms" type="ignored"><max_step_size>0.001</max_step_size><real_time_factor>1.0</real_time_factor></physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <light type="directional" name="sun"><cast_shadows>true</cast_shadows><pose>0 0 10 0 0 0</pose>
      <diffuse>0.8 0.8 0.8 1</diffuse><direction>-0.5 0.1 -0.9</direction></light>
    <model name="ground"><static>true</static><link name="link">
      <collision name="c"><geometry><plane><normal>0 0 1</normal><size>{W+2} {H+2}</size></plane></geometry></collision>
      <visual name="v"><geometry><plane><normal>0 0 1</normal><size>{W+2} {H+2}</size></plane></geometry></visual>
    </link><pose>{W/2} {H/2} 0 0 0 0</pose></model>
{spawn}
{chr(10).join(models)}
  </world>
</sdf>
"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=10_000_072, help="episode seed (test missions: 10000000 + i)")
    ap.add_argument("--out", default="radsearch_world.sdf")
    a = ap.parse_args()
    core = RadSearchCore(EnvConfig(n_particles=100), 1, autoreset=False)
    core.reset_env(0, seed=a.seed)
    open(a.out, "w").write(layout_to_sdf(core))
    print("wrote", a.out)
