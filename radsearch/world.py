"""Room layouts: grid, rectangular obstacles, start cells and source placement.

FR-ENV-02 (20x20 grid, 0-7 rectangles), FR-ENV-09 (random or fixed-grid
source placement), FR-ENV-10 (curriculum knobs: obstacle count).

Design decisions (see docs/DESIGN_DECISIONS.md, D4):
* Obstacles never overlap (overlap would double-count attenuation) and must
  keep the free space 4-connected, so every source is reachable.
* Robots enter through a "door" on a random wall and start on the free cells
  closest to it -- this mirrors real deployments and makes the perimeter
  baseline meaningful. ``start_mode="random"`` is available for ablations.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np

# action id -> (dx, dy). 4 = stay-and-measure (FR-ENV-04)
MOVES = np.array([[0, 1], [0, -1], [-1, 0], [1, 0], [0, 0]], dtype=np.int64)
ACTION_NAMES = ["up", "down", "left", "right", "stay", "withdraw"]
N_ACTIONS = 5          # movement actions; the optional withdraw action (K0.1) is index 5
WITHDRAW = 5


@dataclass
class Layout:
    width: int
    height: int
    cell: float
    occ: np.ndarray  # (W, H) bool, occ[x, y]
    rects: np.ndarray  # (K, 4) metres, [xmin, ymin, xmax, ymax]
    materials: list
    start_cells: np.ndarray  # (N, 2) int
    door: tuple

    @property
    def free_cells(self) -> np.ndarray:
        return np.argwhere(~self.occ)

    def cell_center(self, cells) -> np.ndarray:
        return (np.asarray(cells, dtype=np.float64) + 0.5) * self.cell


def bfs_distances(occ: np.ndarray, start) -> np.ndarray:
    """Grid BFS (4-neighbour) distances from ``start``; unreachable = -1."""
    W, H = occ.shape
    dist = -np.ones((W, H), dtype=np.int64)
    if occ[start[0], start[1]]:
        return dist
    dist[start[0], start[1]] = 0
    q = deque([tuple(start)])
    while q:
        x, y = q.popleft()
        for dx, dy in MOVES[:4]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and not occ[nx, ny] and dist[nx, ny] < 0:
                dist[nx, ny] = dist[x, y] + 1
                q.append((nx, ny))
    return dist


def _connected(occ: np.ndarray) -> bool:
    """Free space is one 4-connected component (scipy.ndimage, C speed)."""
    from scipy.ndimage import label
    _, n = label(~occ)
    return n == 1


def _door_cells(W: int, H: int):
    cells = [(x, 0) for x in range(W)] + [(x, H - 1) for x in range(W)]
    cells += [(0, y) for y in range(1, H - 1)] + [(W - 1, y) for y in range(1, H - 1)]
    return cells


def generate_layout(rng: np.random.Generator, n_agents: int, width: int = 20, height: int = 20,
                    cell: float = 1.0, n_obstacles=(0, 7), max_obstacle_size: int = 4,
                    materials=("concrete",), start_mode: str = "door",
                    start_clearance: int = 2, max_tries: int = 200) -> Layout:
    """Sample a room. ``n_obstacles`` is an int or an inclusive (lo, hi) range."""
    if np.isscalar(n_obstacles):
        k_target = int(n_obstacles)
    else:
        k_target = int(rng.integers(n_obstacles[0], n_obstacles[1] + 1))
    doors = _door_cells(width, height)
    door = doors[int(rng.integers(len(doors)))]

    occ = np.zeros((width, height), dtype=bool)
    # cells near the door are kept free so robots can always enter
    gx, gy = np.meshgrid(np.arange(width), np.arange(height), indexing="ij")
    keep_free = (np.abs(gx - door[0]) + np.abs(gy - door[1])) <= start_clearance + int(np.ceil(np.sqrt(n_agents)))

    rects, mats = [], []
    tries = 0
    while len(rects) < k_target and tries < max_tries:
        tries += 1
        w = int(rng.integers(1, max_obstacle_size + 1))
        h = int(rng.integers(1, max_obstacle_size + 1))
        x0 = int(rng.integers(0, width - w + 1))
        y0 = int(rng.integers(0, height - h + 1))
        block = np.zeros_like(occ)
        block[x0:x0 + w, y0:y0 + h] = True
        if (block & (occ | keep_free)).any():
            continue
        new = occ | block
        if not _connected(new):
            continue
        occ = new
        rects.append([x0 * cell, y0 * cell, (x0 + w) * cell, (y0 + h) * cell])
        mats.append(materials[int(rng.integers(len(materials)))])

    start_cells = place_starts(rng, occ, door, n_agents, start_mode)
    return Layout(width, height, cell, occ, np.array(rects, dtype=np.float64).reshape(-1, 4),
                  mats, start_cells, door)


def place_starts(rng, occ, door, n_agents, mode="door") -> np.ndarray:
    if mode == "door":
        dist = bfs_distances(occ, door)
        free = np.argwhere(dist >= 0)
        # nearest free cells to the door; random tie-break keeps variety
        key = dist[free[:, 0], free[:, 1]] + rng.random(len(free)) * 0.5
        return free[np.argsort(key)[:n_agents]]
    if mode == "random":
        free = np.argwhere(~occ)
        return free[rng.choice(len(free), size=n_agents, replace=False)]
    raise ValueError(f"unknown start_mode {mode}")


def sample_source(rng, layout: Layout, min_dist: float = 5.0, continuous: bool = True) -> np.ndarray:
    """Random source position in a free cell at least ``min_dist`` from every start."""
    free = layout.free_cells
    starts = layout.cell_center(layout.start_cells)
    centers = layout.cell_center(free)
    dmin = np.min(np.linalg.norm(centers[:, None] - starts[None], axis=-1), axis=1)
    ok = free[dmin >= min_dist]
    if len(ok) == 0:
        ok = free[np.argsort(-dmin)[:1]]
    c = ok[int(rng.integers(len(ok)))]
    if continuous:
        return (c + rng.uniform(0.05, 0.95, size=2)) * layout.cell
    return layout.cell_center(c)


def source_grid(layout: Layout) -> np.ndarray:
    """All free cell centres (every 1 m) for systematic evaluation (FR-ENV-09)."""
    return layout.cell_center(layout.free_cells)


def ring_waypoints(occ: np.ndarray, inset: int = 0) -> np.ndarray:
    """Free cells on the ring ``inset`` cells from the walls, clockwise from (inset, inset)."""
    W, H = occ.shape
    a, bx, by = inset, W - 1 - inset, H - 1 - inset
    ring = [(a, y) for y in range(a, by + 1)]           # up the left wall
    ring += [(x, by) for x in range(a + 1, bx + 1)]     # along the top
    ring += [(bx, y) for y in range(by - 1, a - 1, -1)]  # down the right wall
    ring += [(x, a) for x in range(bx - 1, a, -1)]      # back along the bottom
    return np.array([c for c in ring if not occ[c]], dtype=np.int64)
