"""Evaluate one training run with the exact env config it was trained on
(+ optional overrides for generalisation tests, FR-EVAL-05)."""
import argparse
import json
import os

from omegaconf import OmegaConf

from radsearch.algos.policy import load_policy
from radsearch.evaluate import evaluate_grid, evaluate_policy
from radsearch.train import to_env_cfg

ap = argparse.ArgumentParser()
ap.add_argument("--run", required=True)
ap.add_argument("--episodes", type=int, default=1000)
ap.add_argument("--set", nargs="*", default=[])
ap.add_argument("--tag", default="test")
ap.add_argument("--grid", action="store_true")
a = ap.parse_args()
cfg = OmegaConf.load(os.path.join(a.run, "hydra_config.yaml")).env
cfg = OmegaConf.merge(cfg, OmegaConf.from_dotlist(a.set))
env_cfg = to_env_cfg(cfg)
if env_cfg.n_agents > env_cfg.max_agents:
    raise SystemExit(f"policy was built for at most max_agents={env_cfg.max_agents} robots; "
                     "train with a larger env.max_agents to test more robots")
pol = load_policy(os.path.join(a.run, "checkpoints", "final.pt"))
res = dict(run=a.run, tag=a.tag, overrides=a.set,
           test=evaluate_policy(pol, env_cfg, a.episodes, keep_episodes=True))
if a.grid:
    res["grid"] = evaluate_grid(pol, env_cfg)
with open(os.path.join(a.run, f"eval_{a.tag}.json"), "w") as f:
    json.dump(res, f)
print(a.run, a.tag, json.dumps(res["test"]["metrics"]))
