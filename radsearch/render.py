"""Dose-rate heat map and trajectory animation (FR-ENV-08)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LogNorm  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402


def dose_rate_map(core, b: int, res: float = 0.25):
    cfg = core.cfg
    xs = np.arange(res / 2, cfg.width * cfg.cell, res)
    ys = np.arange(res / 2, cfg.height * cfg.cell, res)
    gx, gy = np.meshgrid(xs, ys, indexing="ij")
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    return xs, ys, core.true_dose_rate(b, pts).reshape(gx.shape)


def _draw(ax, core, b, traj, particles=True):
    cfg = core.cfg
    xs, ys, rate = dose_rate_map(core, b)
    im = ax.pcolormesh(xs, ys, rate.T, norm=LogNorm(vmin=max(rate.min(), 1e-6), vmax=rate.max()),
                       cmap="magma", shading="auto")
    for r in core.rects[b, :core.nrect[b]]:
        ax.add_patch(Rectangle(r[:2], r[2] - r[0], r[3] - r[1], color="#7f8c8d", zorder=3))
    if particles:
        p = core.pf.subsample(b, 300, np.random.default_rng(0))
        ax.scatter(p[:, 0], p[:, 1], s=1, c="cyan", alpha=0.4, zorder=4)
    cmap = plt.get_cmap("tab10")
    if traj is not None and len(traj):
        bud = core.budget[b]
        for i in range(traj.shape[1]):
            ax.plot(traj[:, i, 0], traj[:, i, 1], "-", color=cmap(i), lw=1.0 + 2.0 * bud[i] / bud.max(),
                    zorder=5, label=f"r{i}: {core.dose[b, i]:.2f}/{bud[i]:.2f} Gy")
            ax.plot(*traj[-1, i], "o", color=cmap(i), ms=6, mec="k", zorder=6,
                    alpha=1.0 if core.active[b, i] else 0.35)
    ax.plot(*core.src[b], "*", color="lime", ms=14, mec="k", zorder=7)
    mean, _ = core.pf.estimate()
    ax.plot(*mean[b, :2], "x", color="white", ms=10, mew=2, zorder=7)
    ax.set_xlim(0, cfg.width * cfg.cell); ax.set_ylim(0, cfg.height * cfg.cell)
    ax.set_aspect("equal"); ax.legend(loc="lower left", fontsize=6, framealpha=0.85)
    return im


def render_frame(core, b: int, traj=None) -> np.ndarray:
    fig, ax = plt.subplots(figsize=(5.6, 5), dpi=100)
    im = _draw(ax, core, b, traj)
    fig.colorbar(im, ax=ax, fraction=0.046, label="dose rate [Gy/h]")
    ax.set_title(f"step {core.t[b]}   estimate error {core.err[b]:.2f} m", fontsize=10)
    fig.tight_layout()
    fig.canvas.draw()
    img = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()
    plt.close(fig)
    return img


def save_episode_animation(frames, path: str, fps: int = 8):
    """frames: list of RGB arrays (from render_frame) -> GIF/MP4 via matplotlib."""
    from matplotlib import animation
    fig, ax = plt.subplots(figsize=(frames[0].shape[1] / 100, frames[0].shape[0] / 100), dpi=100)
    ax.axis("off")
    im = ax.imshow(frames[0])
    anim = animation.FuncAnimation(fig, lambda i: [im.set_data(frames[i])], frames=len(frames))
    writer = "pillow" if path.endswith(".gif") else "ffmpeg"
    anim.save(path, writer=writer, fps=fps)
    plt.close(fig)
