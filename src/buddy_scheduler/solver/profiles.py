"""Solver profile configuration for the PuLP/CBC MIP solver."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SolverProfile(Enum):
    """MIP solver profile controlling gap tolerance and time limits."""

    FAST = "fast"
    BALANCED = "balanced"
    OPTIMAL = "optimal"
    ADAPTIVE = "adaptive"


@dataclass
class ProfileConfig:
    """CBC solver configuration for a given profile."""

    gap_tolerance: float
    time_limit_s: int
    cbc_options: list[str] = field(default_factory=list)


_FAST_CONFIG = ProfileConfig(
    gap_tolerance=0.20,
    time_limit_s=10,
    cbc_options=[],
)

_BALANCED_CONFIG = ProfileConfig(
    gap_tolerance=0.01,
    time_limit_s=60,
    cbc_options=[],
)

_OPTIMAL_CONFIG = ProfileConfig(
    gap_tolerance=0.001,
    time_limit_s=300,
    cbc_options=["-strategy", "1", "-depth", "10000", "-cuts", "all"],
)


def get_profile_config(profile: SolverProfile, n_active: int) -> ProfileConfig:
    """Return the CBC configuration for the given profile and team size.

    For ``ADAPTIVE``, thresholds are:

    - N ≤ 15  → OPTIMAL
    - 16 ≤ N ≤ 60 → BALANCED
    - N > 60  → FAST
    """
    if profile is SolverProfile.FAST:
        return _FAST_CONFIG
    if profile is SolverProfile.BALANCED:
        return _BALANCED_CONFIG
    if profile is SolverProfile.OPTIMAL:
        return _OPTIMAL_CONFIG
    # ADAPTIVE: select based on team size
    if n_active <= 15:
        return _OPTIMAL_CONFIG
    if n_active <= 60:
        return _BALANCED_CONFIG
    return _FAST_CONFIG
