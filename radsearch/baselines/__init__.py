"""Rule-based baselines (FR-BSL-01..05).

Every policy exposes ``act(core) -> (B, N) int actions`` and reads only
deployable information (robot states, map, particle filter) -- never the true
source. ``tests/test_baselines.py`` checks this by scrambling the truth.
"""
from .policies import (ApproachPolicy, GreedyInfoPolicy, PerimeterPolicy, RandomPolicy,
                       make_baseline)

__all__ = ["RandomPolicy", "ApproachPolicy", "PerimeterPolicy", "GreedyInfoPolicy", "make_baseline"]
