# ROS 2 + Gazebo setup (for your own computer)

ROS 2 and Gazebo are the standard stack in robotics and the route to the
semester-2 real-robot tests. They could not be installed in the cloud
environment this project was built in (the ROS package servers were
blocked), so **this guide and the bridge design below have not been run yet**.
What *is* tested: the room exporter (`radsearch/sim3d/sdf_export.py`), which
writes valid Gazebo worlds from our missions.

## 1. Install (Ubuntu 24.04, about 30 minutes)

ROS 2 **Jazzy** pairs with Gazebo **Harmonic** on Ubuntu 24.04. On Windows,
use WSL 2 with Ubuntu 24.04; on macOS, use an Ubuntu virtual machine.

```bash
# ROS 2 Jazzy (official instructions: docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
sudo apt install software-properties-common curl
sudo add-apt-repository universe
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list
sudo apt update && sudo apt install ros-jazzy-desktop ros-jazzy-ros-gz

source /opt/ros/jazzy/setup.bash
gz sim shapes.sdf      # a window with simple shapes means Gazebo works
```

## 2. Load one of our missions in Gazebo (works today)

```bash
pip install -e ".[sim3d]"
python -m radsearch.sim3d.sdf_export --seed 10000072 --out mission72.sdf
gz sim mission72.sdf
```

You get the same room as test mission 72: concrete obstacles, walls, and a
green marker at the true source. The robot start positions are written as
comments at the top of the file.

## 3. Planned bridge (to build next)

```
Gazebo (robot motion, e.g. TurtleBot 4)
   │  /robot_i/odom
   ▼
radiation_sensor_node  ── uses radsearch.physics (same model as training)
   │  /robot_i/counts, /robot_i/dose_rate
   ▼
estimator_node  ── radsearch.estimator.ParticleFilter (shared by the team)
   │  /team/source_estimate
   ▼
policy_node  ── trained MAPPO policy (models/*.pt), one decision per 10 s
   │  /robot_i/goal_pose
   ▼
Nav2 (path planning + control on each robot)
```

The same three nodes later run unchanged on real robots: the "simulated
radiation on real robot positions" option for semester 2. Only the source
of `/robot_i/odom` changes, from Gazebo to the robots' localisation.

## Which simulator for what

| Simulator | Used here for | Status |
|---|---|---|
| Grid simulator (`radsearch.env`) | fast training: thousands of missions | done |
| MuJoCo 3-D (`radsearch.sim3d`) | physical robot motion, collisions; sim-to-sim tests; 3-D renders | done, tested |
| Gazebo + ROS 2 | robotics-standard pipeline; route to real robots | exporter done; bridge planned |
| NVIDIA Isaac Sim | large-scale GPU training (optional) | needs an RTX GPU |
