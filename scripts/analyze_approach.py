"""Do robots approach the source without getting stranded (retired) there?

Re-runs the test episodes with trajectories and reports, per method:
how close robots get, how long they stay near the source, where and when
budget violations (= retirement, robot stranded in place) happen, and whether
robots retreat after their closest approach.
"""
import argparse, json
import numpy as np
from radsearch.evaluate import load_env_cfg, make_policy
from radsearch.eval.runner import run_episodes, test_seeds

ap = argparse.ArgumentParser()
ap.add_argument("--policy", required=True); ap.add_argument("--name", required=True)
ap.add_argument("--episodes", type=int, default=200); ap.add_argument("--out", required=True)
ap.add_argument("--set", nargs="*", default=["budget_base_Gy=0.1"])
a = ap.parse_args()
cfg = load_env_cfg(None, a.set)
eps = run_episodes(make_policy(a.policy), cfg, test_seeds(a.episodes), record_trajectories=True)
rows = []
for e in eps:
    tr = np.array(e["trajectory"]); src = np.array(e["source"])
    d = np.linalg.norm(tr - src, axis=-1)            # (T+1, N)
    for i in range(d.shape[1]):
        vs = e["violation_step"][i]
        rows.append(dict(act=e["activity_TBq"], success=e["success"], steps=e["steps"],
                         dmin=float(d[:, i].min()), near2=int((d[1:, i] <= 2.0).sum()),
                         d_end=float(d[-1, i]), dose_frac=e["dose"][i] / e["budget"][i],
                         violated=e["violated"][i],
                         d_at_viol=float(d[vs + 1, i]) if vs >= 0 else None,
                         t_viol=vs, ep_any=e["any_violation"]))
json.dump(dict(name=a.name, rows=rows, episodes=[{k: v for k, v in e.items() if k != "trajectory"} for e in eps]),
          open(a.out, "w"))
print("done", a.name, len(rows))
