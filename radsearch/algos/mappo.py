"""MAPPO, MAPPO-Lagrangian (per-robot multipliers) and fixed-penalty MAPPO.

FR-ALG-01: parameter-shared actor with one-hot robot ID, centralised critic
           on the agent-specific global state (Yu et al. 2022).
FR-ALG-02: separate cost critic and one Lagrange multiplier per robot.
FR-ALG-03: cost version A -- per-step dose / budget, limit ~0.75.
FR-ALG-04: cost version B -- 1 at the step a robot exceeds its budget,
           limit 0.05, optionally + kappa * dose / budget.
FR-ALG-05: fixed penalty -- handled in the env reward (dose_penalty_beta).
FR-ALG-06: the multiplier update reproduces Safe-Policy-Optimization's
           ``lamda_lagr = max(0, lamda_lagr + lr * (J_c - d))``; a PID
           Lagrangian (Stooke et al. 2020) is available against oscillation.
FR-ALG-07: optional dose shield masks the policy logits during training and
           execution, so stored log-probs match the executed policy.
FR-BUD-04: retired robots' steps are masked out of every loss.

Truncation at the time limit is treated as terminal: the time-left feature is
part of every observation and of the state, so the problem is Markov.
"""
from __future__ import annotations

import copy
import json
import os
import time
from dataclasses import asdict, dataclass, field

import numpy as np
import torch
import torch.nn as nn

from ..env import EnvConfig, RadSearchCore
from ..shield import DoseShield
from ..world import N_ACTIONS


# --------------------------------------------------------------------- config
@dataclass
class AlgoConfig:
    method: str = "mappo_lag"          # mappo | mappo_lag | mappo_penalty
    cost_version: str = "A"            # A | B
    cost_limit: float | None = None    # default: 0.75 (A) / 0.05 (B)
    cost_kappa: float = 0.0            # version B: extra per-step dose cost
    lambda_sharing: str = "per_robot"  # per_robot | shared   (E4 ablation)
    lambda_mode: str = "gd"            # gd | pid
    lambda_lr: float = 0.05
    lambda_init: float = 0.0
    lambda_max: float = 100.0
    pid_kp: float = 0.5
    pid_ki: float = 0.05
    pid_kd: float = 0.0
    penalty_beta: float = 0.0          # mappo_penalty only
    shield: bool = False
    shield_quantile: float = 0.95
    shield_horizon: int = 3
    # PPO
    n_envs: int = 16
    rollout_len: int = 64
    total_env_steps: int = 2_000_000
    lr_actor: float = 5e-4
    lr_critic: float = 5e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip: float = 0.2
    epochs: int = 5
    minibatches: int = 2
    entropy_coef: float = 0.01
    value_coef: float = 1.0
    max_grad_norm: float = 10.0
    hidden: int = 128
    seed: int = 0
    torch_threads: int = 1
    # curriculum (FR-ENV-10): list of {"until": fraction, **EnvConfig overrides}
    curriculum: list = field(default_factory=list)
    # infra
    run_dir: str = "runs/debug"
    checkpoint_every: int = 20
    log_every: int = 1
    wandb_mode: str = "disabled"       # disabled | offline | online
    wandb_project: str = "dose-budgeted-marl"
    init_checkpoint: str | None = None  # warm start (e.g. from MAPPO)

    def limit(self):
        if self.cost_limit is not None:
            return self.cost_limit
        return 0.75 if self.cost_version == "A" else 0.05


# ------------------------------------------------------------------- networks
def mlp(i, h, o, out_gain=1.0):
    layers = [nn.Linear(i, h), nn.Tanh(), nn.Linear(h, h), nn.Tanh(), nn.Linear(h, o)]
    for l in layers:
        if isinstance(l, nn.Linear):
            nn.init.orthogonal_(l.weight, np.sqrt(2)); nn.init.zeros_(l.bias)
    nn.init.orthogonal_(layers[-1].weight, out_gain)
    return nn.Sequential(*layers)


class ValueNorm(nn.Module):
    """Running mean/var normaliser for value targets (MAPPO's ValueNorm)."""

    def __init__(self, beta=0.99999):
        super().__init__()
        self.beta = beta
        self.register_buffer("mean", torch.zeros(1)); self.register_buffer("sq", torch.zeros(1))
        self.register_buffer("debias", torch.zeros(1))

    def update(self, x):
        b = self.beta
        self.mean.mul_(b).add_(x.mean() * (1 - b)); self.sq.mul_(b).add_((x ** 2).mean() * (1 - b))
        self.debias.mul_(b).add_(1 - b)

    def stats(self):
        m = self.mean / self.debias.clamp(min=1e-5); v = self.sq / self.debias.clamp(min=1e-5) - m ** 2
        return m, v.clamp(min=1e-2).sqrt()

    def normalize(self, x):
        m, s = self.stats(); return (x - m) / s

    def denormalize(self, x):
        m, s = self.stats(); return x * s + m


class ActorCritic(nn.Module):
    def __init__(self, obs_dim, state_dim, max_agents, hidden, cost_critic=True):
        super().__init__()
        self.M = max_agents
        self.actor = mlp(obs_dim + max_agents, hidden, N_ACTIONS, out_gain=0.01)
        self.critic = mlp(state_dim + obs_dim + max_agents, hidden, 1)
        self.vnorm = ValueNorm()
        self.has_cost = cost_critic
        if cost_critic:
            self.ccritic = mlp(state_dim + obs_dim + max_agents, hidden, 1)
            self.cnorm = ValueNorm()

    def actor_in(self, obs):
        B, N = obs.shape[:2]
        ids = torch.eye(self.M)[:N].expand(B, N, self.M)
        return torch.cat([obs, ids], -1)

    def critic_in(self, obs, state):
        return torch.cat([state, self.actor_in(obs)], -1)

    def dist(self, obs, mask=None):
        logits = self.actor(self.actor_in(obs))
        if mask is not None:
            logits = logits.masked_fill(~mask, -1e9)
        return torch.distributions.Categorical(logits=logits)

    def values(self, obs, state):
        x = self.critic_in(obs, state)
        v = self.critic(x)[..., 0]
        c = self.ccritic(x)[..., 0] if self.has_cost else torch.zeros_like(v)
        return v, c


# ----------------------------------------------------------------- multipliers
class Lagrange:
    """Per-robot (or shared) multipliers; projected gradient ascent or PID."""

    def __init__(self, n, cfg: AlgoConfig):
        self.cfg = cfg
        self.lam = np.full(n, cfg.lambda_init, float)
        self.integral = np.zeros(n); self.prev = np.zeros(n)

    def update(self, Jc: np.ndarray, valid: np.ndarray):
        c, d = self.cfg, self.cfg.limit()
        if c.lambda_sharing == "shared":
            if not valid.any():
                return
            e = np.full_like(self.lam, Jc[valid].mean() - d); valid = np.ones_like(valid)
        else:
            e = Jc - d
        if c.lambda_mode == "gd":
            new = np.maximum(0.0, self.lam + c.lambda_lr * e)
        else:
            self.integral = np.where(valid, np.maximum(0.0, self.integral + e), self.integral)
            deriv = np.where(valid, e - self.prev, 0.0)
            new = np.maximum(0.0, c.pid_kp * e + c.pid_ki * self.integral + c.pid_kd * deriv)
            self.prev = np.where(valid, e, self.prev)
        self.lam = np.where(valid, np.minimum(new, c.lambda_max), self.lam)

    def state_dict(self):
        return dict(lam=self.lam.tolist(), integral=self.integral.tolist(), prev=self.prev.tolist())

    def load_state_dict(self, d):
        self.lam, self.integral, self.prev = (np.array(d[k]) for k in ("lam", "integral", "prev"))


# --------------------------------------------------------------------- logger
class Logger:
    def __init__(self, run_dir, cfg_dict, mode="disabled", project=None):
        self.path = os.path.join(run_dir, "metrics.jsonl")
        self.wb = None
        if mode != "disabled":
            try:
                import wandb
                self.wb = wandb.init(project=project, dir=run_dir, config=cfg_dict, mode=mode,
                                     name=os.path.basename(run_dir.rstrip("/")), resume="allow",
                                     id=os.path.basename(run_dir.rstrip("/")).replace("/", "_"))
            except Exception as e:  # pragma: no cover
                print(f"[logger] wandb disabled: {e}")

    def log(self, d):
        with open(self.path, "a") as f:
            f.write(json.dumps(d) + "\n")
        if self.wb is not None:
            self.wb.log(d, step=d.get("env_steps"))


# -------------------------------------------------------------------- trainer
class MAPPOTrainer:
    def __init__(self, env_cfg: EnvConfig, cfg: AlgoConfig):
        self.base_env_cfg = copy.deepcopy(env_cfg)
        self.cfg = cfg
        torch.set_num_threads(cfg.torch_threads)
        torch.manual_seed(cfg.seed)
        np.random.seed(cfg.seed)
        if cfg.method == "mappo_penalty":
            self.base_env_cfg.dose_penalty_beta = cfg.penalty_beta
        self.stage = -1
        self.core = None
        self._set_stage(0.0)
        M = self.base_env_cfg.max_agents
        self.net = ActorCritic(self.core.obs_dim, self.core.state_dim, M, cfg.hidden,
                               cost_critic=self.constrained)
        self.opt_a = torch.optim.Adam(self.net.actor.parameters(), lr=cfg.lr_actor, eps=1e-5)
        cparams = list(self.net.critic.parameters()) + (list(self.net.ccritic.parameters()) if self.constrained else [])
        self.opt_c = torch.optim.Adam(cparams, lr=cfg.lr_critic, eps=1e-5)
        self.lagr = Lagrange(M, cfg)
        self.shield = DoseShield(cfg.shield_quantile, cfg.shield_horizon, seed=cfg.seed) if cfg.shield else None
        self.env_steps, self.updates = 0, 0
        self.ep_buffer = []
        os.makedirs(os.path.join(cfg.run_dir, "checkpoints"), exist_ok=True)
        self.ckpt_path = os.path.join(cfg.run_dir, "checkpoints", "latest.pt")
        if os.path.exists(self.ckpt_path):
            self.load(self.ckpt_path)          # FR-INF-03: automatic resume
            print(f"[trainer] resumed from {self.ckpt_path} at {self.env_steps} env steps")
        elif cfg.init_checkpoint:
            self.load(cfg.init_checkpoint, weights_only=True)
        with open(os.path.join(cfg.run_dir, "config.json"), "w") as f:
            json.dump(dict(env=asdict(self.base_env_cfg), algo=asdict(cfg)), f, indent=1, default=str)
        self.logger = Logger(cfg.run_dir, dict(env=asdict(self.base_env_cfg), algo=asdict(cfg)),
                             cfg.wandb_mode, cfg.wandb_project)

    @property
    def constrained(self):
        return self.cfg.method == "mappo_lag"

    # ------------------------------------------------------------ curriculum
    def _set_stage(self, progress):
        stages = self.cfg.curriculum or [{"until": 1.0}]
        k = next((i for i, s in enumerate(stages) if progress < s["until"]), len(stages) - 1)
        if k == self.stage:
            return
        self.stage = k
        ecfg = copy.deepcopy(self.base_env_cfg)
        for key, val in stages[k].items():
            if key != "until":
                setattr(ecfg, key, tuple(val) if isinstance(val, list) else val)
        self.env_cfg = ecfg
        self.core = RadSearchCore(ecfg, self.cfg.n_envs, seed=self.cfg.seed * 1000 + k)
        self.obs, self.state = self.core.reset_all()
        self.ep_cost = np.zeros((self.cfg.n_envs, ecfg.n_agents))
        print(f"[trainer] curriculum stage {k}: " + json.dumps({k2: v for k2, v in stages[k].items()}))

    # ---------------------------------------------------------------- costs
    def _cost(self, out):
        if self.cfg.cost_version == "A":
            return out["cost_dose"]
        return out["cost_violation"] + self.cfg.cost_kappa * out["cost_dose"]

    # -------------------------------------------------------------- rollout
    @torch.no_grad()
    def collect(self):
        T, B, N = self.cfg.rollout_len, self.cfg.n_envs, self.env_cfg.n_agents
        buf = {k: [] for k in ("obs", "state", "act", "logp", "amask", "acting", "rew", "cost",
                               "term", "v", "c")}
        for t in range(T):
            amask = self.core.action_mask()
            if self.shield is not None:
                amask &= self.shield.mask(self.core)
            obs_t = torch.as_tensor(self.obs); st_t = torch.as_tensor(self.state)
            am_t = torch.as_tensor(amask)
            d = self.net.dist(obs_t, am_t)
            a = d.sample()
            v, c = self.net.values(obs_t, st_t)
            out = self.core.step(a.numpy())
            cost = self._cost(out)
            self.ep_cost += cost * out["acting"]
            # agent-level terminal: env done, or this robot retired this step
            term = out["done"][:, None] | (out["acting"] & ~out["active"])
            # out["active"] is post-reset for done envs; done covers those
            for k, val in (("obs", obs_t), ("state", st_t), ("act", a), ("logp", d.log_prob(a)),
                           ("amask", am_t), ("acting", out["acting"]), ("rew", out["reward"]),
                           ("cost", cost), ("term", term), ("v", v), ("c", c)):
                buf[k].append(torch.as_tensor(np.asarray(val)) if not torch.is_tensor(val) else val)
            for ep, b in zip(out["episodes"], np.flatnonzero(out["done"])):
                ep["cost"] = self.ep_cost[b].tolist()
                self.ep_buffer.append(ep)
                self.ep_cost[b] = 0.0
            self.obs, self.state = out["obs"], out["state"]
            self.env_steps += B
        v_last, c_last = self.net.values(torch.as_tensor(self.obs), torch.as_tensor(self.state))
        buf = {k: torch.stack(v) for k, v in buf.items()}
        buf["v_last"], buf["c_last"] = v_last, c_last
        return buf

    def _gae(self, rew, values, last, term, norm):
        """rew (T,B,N) or broadcastable; values raw-normalised; returns adv, returns."""
        T = rew.shape[0]
        vals = norm.denormalize(values); last = norm.denormalize(last)
        adv = torch.zeros_like(vals); gae = torch.zeros_like(last)
        for t in reversed(range(T)):
            nv = last if t == T - 1 else vals[t + 1]
            nonterm = 1.0 - term[t].float()
            delta = rew[t] + self.cfg.gamma * nv * nonterm - vals[t]
            gae = delta + self.cfg.gamma * self.cfg.gae_lambda * nonterm * gae
            adv[t] = gae
        return adv, adv + vals

    # --------------------------------------------------------------- update
    def update(self, buf):
        cfg = self.cfg
        N = self.env_cfg.n_agents
        rew = buf["rew"][..., None].expand(-1, -1, N).float()
        adv_r, ret_r = self._gae(rew, buf["v"], buf["v_last"], buf["term"], self.net.vnorm)
        mask = buf["acting"].float()
        if self.constrained:
            adv_c, ret_c = self._gae(buf["cost"].float(), buf["c"], buf["c_last"], buf["term"], self.net.cnorm)
        m = mask.bool()
        adv_r_n = (adv_r - adv_r[m].mean()) / (adv_r[m].std() + 1e-8)
        if self.constrained:
            adv_c_n = (adv_c - adv_c[m].mean()) / (adv_c[m].std() + 1e-8)
            lam = torch.as_tensor(self.lagr.lam[:N], dtype=torch.float32)
            adv = (adv_r_n - lam * adv_c_n) / (1.0 + lam)
        else:
            adv = adv_r_n
        self.net.vnorm.update(ret_r[m])
        if self.constrained:
            self.net.cnorm.update(ret_c[m])
        tr = self.net.vnorm.normalize(ret_r)
        tc = self.net.cnorm.normalize(ret_c) if self.constrained else None
        flat = lambda x: x.reshape(-1, *x.shape[3:]) if x.dim() > 3 else x.reshape(-1)
        # minibatch over (T,B) env-steps, keeping all agents of a step together
        T, B = buf["rew"].shape
        idx_all = np.arange(T * B)
        stats = []
        for _ in range(cfg.epochs):
            np.random.shuffle(idx_all)
            for mb in np.array_split(idx_all, cfg.minibatches):
                sel = lambda x: x.reshape(T * B, *x.shape[2:])[mb]
                obs, st, act, oldlp = sel(buf["obs"]), sel(buf["state"]), sel(buf["act"]), sel(buf["logp"])
                am, mk, A = sel(buf["amask"]), sel(mask), sel(adv)
                d = self.net.dist(obs, am)
                lp = d.log_prob(act)
                ratio = torch.exp(lp - oldlp)
                s1 = ratio * A; s2 = torch.clamp(ratio, 1 - cfg.clip, 1 + cfg.clip) * A
                denom = mk.sum().clamp(min=1.0)
                pol_loss = -(torch.min(s1, s2) * mk).sum() / denom
                ent = (d.entropy() * mk).sum() / denom
                self.opt_a.zero_grad()
                (pol_loss - cfg.entropy_coef * ent).backward()
                nn.utils.clip_grad_norm_(self.net.actor.parameters(), cfg.max_grad_norm)
                self.opt_a.step()
                v, c = self.net.values(obs, st)
                vl = (((v - sel(tr)) ** 2) * mk).sum() / denom
                cl = (((c - sel(tc)) ** 2) * mk).sum() / denom if self.constrained else torch.zeros(())
                self.opt_c.zero_grad()
                (cfg.value_coef * (vl + cl)).backward()
                nn.utils.clip_grad_norm_(list(self.net.critic.parameters()) +
                                         (list(self.net.ccritic.parameters()) if self.constrained else []),
                                         cfg.max_grad_norm)
                self.opt_c.step()
                with torch.no_grad():
                    kl = ((oldlp - lp) * mk).sum() / denom
                stats.append([pol_loss.item(), vl.item(), cl.item(), ent.item(), kl.item()])
        return dict(zip(["pol_loss", "v_loss", "c_loss", "entropy", "approx_kl"], np.mean(stats, 0).tolist()))

    # ------------------------------------------------------------------ loop
    def train(self):
        cfg = self.cfg
        t0 = time.time()
        while self.env_steps < cfg.total_env_steps:
            self._set_stage(self.env_steps / cfg.total_env_steps)
            buf = self.collect()
            stats = self.update(buf)
            eps = self.ep_buffer; self.ep_buffer = []
            N = self.env_cfg.n_agents
            if self.constrained and eps:
                Jc = np.array([e["cost"] for e in eps if e["n_agents"] == N]).mean(0)
                Jfull = np.zeros(self.base_env_cfg.max_agents); Jfull[:N] = Jc
                valid = np.zeros(self.base_env_cfg.max_agents, bool); valid[:N] = True
                self.lagr.update(Jfull, valid)
            self.updates += 1
            if eps and self.updates % cfg.log_every == 0:
                log = dict(env_steps=self.env_steps, updates=self.updates, stage=self.stage,
                           fps=self.env_steps / max(time.time() - t0, 1e-9) if self.updates == 1 else None,
                           episodes=len(eps),
                           ret=float(np.mean([e["ret"] for e in eps])),
                           success=float(np.mean([e["success"] for e in eps])),
                           error=float(np.median([e["error"] for e in eps])),
                           violation=float(np.mean([e["any_violation"] for e in eps])),
                           max_dose_frac=float(np.mean([np.max(np.array(e["dose"]) / np.array(e["budget"])) for e in eps])),
                           ep_len=float(np.mean([e["steps"] for e in eps])),
                           cost=np.mean([e["cost"] for e in eps], 0).tolist(),
                           lam=self.lagr.lam[:N].tolist(), wall=time.time() - t0, **stats)
                log["fps"] = self.env_steps / (time.time() - t0)
                self.logger.log(log)
                print(f"[{self.env_steps:>8d}] ret {log['ret']:+.3f} succ {log['success']:.2f} "
                      f"viol {log['violation']:.2f} dosefrac {log['max_dose_frac']:.2f} len {log['ep_len']:.0f} "
                      f"lam {np.round(log['lam'], 3).tolist()} kl {stats['approx_kl']:.4f}", flush=True)
            if self.updates % cfg.checkpoint_every == 0:
                self.save(self.ckpt_path)
        self.save(self.ckpt_path)
        self.save(os.path.join(cfg.run_dir, "checkpoints", "final.pt"))
        return self

    # ------------------------------------------------------------ checkpoint
    def save(self, path):
        tmp = path + ".tmp"
        torch.save(dict(net=self.net.state_dict(), opt_a=self.opt_a.state_dict(),
                        opt_c=self.opt_c.state_dict(), lagr=self.lagr.state_dict(),
                        env_steps=self.env_steps, updates=self.updates,
                        np_rng=np.random.get_state(), torch_rng=torch.get_rng_state(),
                        env_cfg=asdict(self.base_env_cfg), algo_cfg=asdict(self.cfg),
                        obs_dim=self.core.obs_dim, state_dim=self.core.state_dim), tmp)
        os.replace(tmp, path)  # atomic: a killed job never leaves a corrupt checkpoint

    def load(self, path, weights_only=False):
        ck = torch.load(path, weights_only=False)
        if not weights_only and ck["algo_cfg"]["method"] != self.cfg.method:
            raise RuntimeError(f"{path} was written by method={ck['algo_cfg']['method']}, "
                               f"not {self.cfg.method}; use a fresh run_dir")
        self.net.load_state_dict(ck["net"], strict=False)
        if weights_only:
            return
        self.opt_a.load_state_dict(ck["opt_a"]); self.opt_c.load_state_dict(ck["opt_c"])
        self.lagr.load_state_dict(ck["lagr"])
        self.env_steps, self.updates = ck["env_steps"], ck["updates"]
        np.random.set_state(ck["np_rng"]); torch.set_rng_state(ck["torch_rng"])
