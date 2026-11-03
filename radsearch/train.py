"""Hydra entry point:  python -m radsearch.train algo=mappo_lag_a env=main seed=3"""
from __future__ import annotations

import json
import os

import hydra
from omegaconf import DictConfig, OmegaConf

from .algos.mappo import AlgoConfig, MAPPOTrainer
from .env import EnvConfig


def to_env_cfg(c) -> EnvConfig:
    d = OmegaConf.to_container(c, resolve=True)
    d.pop("name", None)
    for k, v in d.items():
        if isinstance(v, list):
            d[k] = tuple(v)
    return EnvConfig(**d)


def to_algo_cfg(c, run_dir, seed) -> AlgoConfig:
    d = OmegaConf.to_container(c, resolve=True)
    d.pop("name", None)
    d.update(run_dir=run_dir, seed=seed)
    return AlgoConfig(**d)


@hydra.main(version_base=None, config_path="../conf", config_name="config")
def main(cfg: DictConfig):
    os.makedirs(cfg.run_dir, exist_ok=True)
    with open(os.path.join(cfg.run_dir, "hydra_config.yaml"), "w") as f:
        f.write(OmegaConf.to_yaml(cfg, resolve=True))
    env_cfg = to_env_cfg(cfg.env)
    trainer = MAPPOTrainer(env_cfg, to_algo_cfg(cfg.algo, cfg.run_dir, cfg.seed)).train()
    if cfg.eval_after_training:
        from .evaluate import evaluate_policy
        from .algos.policy import load_policy
        pol = load_policy(os.path.join(cfg.run_dir, "checkpoints", "final.pt"))
        res = evaluate_policy(pol, env_cfg, n_episodes=cfg.eval_episodes)
        with open(os.path.join(cfg.run_dir, "eval_test.json"), "w") as f:
            json.dump(res, f)
        print(json.dumps(res["metrics"], indent=1))
    return trainer


if __name__ == "__main__":
    main()
