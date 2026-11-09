"""Trained-policy wrapper with the baseline interface ``act(core)``."""
from __future__ import annotations

import numpy as np
import torch

from ..shield import DoseShield
from .mappo import ActorCritic


class LearnedPolicy:
    def __init__(self, net: ActorCritic, deterministic: bool = True, shield: DoseShield | None = None,
                 seed: int = 0, name: str = "learned", with_pred: bool = False):
        self.net, self.det, self.shield, self.name = net, deterministic, shield, name
        self.with_pred = with_pred   # observation layout the policy was trained with
        self.gen = torch.Generator().manual_seed(seed)

    def reset(self, core, b):
        pass

    @torch.no_grad()
    def act(self, core):
        obs, _ = core.observe(with_pred=self.with_pred)
        mask = core.action_mask()
        if self.shield is not None:
            mask &= self.shield.mask(core)
        d = self.net.dist(torch.as_tensor(obs), torch.as_tensor(mask))
        if self.det:
            return d.probs.argmax(-1).numpy()
        return torch.multinomial(d.probs.reshape(-1, d.probs.shape[-1]), 1, generator=self.gen
                                 ).reshape(d.probs.shape[:-1]).numpy()


def load_policy(path: str, deterministic: bool = True, seed: int = 0) -> LearnedPolicy:
    ck = torch.load(path, weights_only=False)
    a = ck["algo_cfg"]; e = ck["env_cfg"]
    net = ActorCritic(ck["obs_dim"], ck["state_dim"], e["max_agents"], a["hidden"],
                      cost_critic=a["method"] == "mappo_lag", n_actions=ck.get("n_actions", 5))
    net.load_state_dict(ck["net"])
    net.eval()
    shield = DoseShield(a["shield_quantile"], a["shield_horizon"], seed=seed) if a["shield"] else None
    return LearnedPolicy(net, deterministic, shield, seed, name=a["method"],
                         with_pred=bool(e.get("obs_predicted_dose", False)))
