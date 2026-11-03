# Trained models

Single-seed sanity runs (not paper results). Main setting with a 0.1 Gy budget,
Co-60, 4 robots, correlated detector error (σ = 0.3).

| file | method | training steps | test success | some robot over budget |
|---|---|---|---|---|
| `mappo_sanity_0.1Gy.pt` | MAPPO (no safety rule) | 300 k | 85 % | 9 % |
| `mappo_lag_b_sanity_0.1Gy.pt` | MAPPO-Lagrangian, version B (before the d/N fix) | 150 k | 76 % | 7 % |

Watch one: `python scripts/demo.py --policy models/mappo_sanity_0.1Gy.pt --seed 3`
