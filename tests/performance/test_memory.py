"""Memory metric tests for the buddy-pairing solver.

Verifies that ``peak_memory_mb`` and ``memory_delta_mb`` are populated,
non-negative, scale with team size, and stay within the 200 MB ceiling for a
50-member full-history run.

All tests are marked ``slow`` and excluded from the default ``pytest`` run.
Run explicitly with ``pytest -m slow tests/performance/test_memory.py``.
"""

from __future__ import annotations

import pytest

from buddy_scheduler.models import PairingHistory, TeamMember
from buddy_scheduler.solver.mip import solve_pairing
from buddy_scheduler.solver.profiles import SolverProfile

from .conftest import make_team

# Measured at ~23.4 MB on a 50-member full-history run (stable across runs).
# 50 MB gives ~2× headroom for GC variance and CI hardware differences while
# still catching meaningful regressions.
PEAK_MEMORY_UPPER_BOUND_MB: float = 50.0


@pytest.mark.slow
def test_memory_fields_populated() -> None:
    """Both memory fields are populated and non-negative after a successful solve."""
    members = make_team(10)
    result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.ADAPTIVE)

    assert result.success
    assert result.peak_memory_mb is not None
    assert result.peak_memory_mb > 0
    assert result.memory_delta_mb is not None
    assert result.memory_delta_mb >= 0


@pytest.mark.slow
def test_memory_fields_populated_min_team() -> None:
    """Memory fields are non-negative for the minimum valid team size (2 members)."""
    members = make_team(2)
    result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.ADAPTIVE)

    assert result.success
    assert result.peak_memory_mb is not None
    assert result.peak_memory_mb > 0
    assert result.memory_delta_mb is not None
    assert result.memory_delta_mb >= 0


@pytest.mark.slow
def test_memory_scales_with_team_size() -> None:
    """A 50-member team uses at least as much memory delta as a 6-member team."""
    small_members = make_team(6)
    large_members = make_team(50)

    small_result = solve_pairing(
        small_members, 0.0, 0.0, None, set(), SolverProfile.ADAPTIVE
    )
    large_result = solve_pairing(
        large_members, 0.0, 0.0, None, set(), SolverProfile.ADAPTIVE
    )

    assert small_result.success and large_result.success
    assert small_result.memory_delta_mb is not None
    assert large_result.memory_delta_mb is not None
    assert large_result.memory_delta_mb >= small_result.memory_delta_mb


@pytest.mark.slow
def test_peak_memory_upper_bound_50_members() -> None:
    """Peak RSS stays below 200 MB for a 50-member team with a full history."""
    n = 50
    members = make_team(n)
    history = PairingHistory()
    names = [m.name for m in members]
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            history.increment_pair(a, b)

    result = solve_pairing(
        members, 1.0, 0.0, history, set(), SolverProfile.ADAPTIVE
    )

    assert result.success
    assert result.peak_memory_mb is not None
    assert result.peak_memory_mb < PEAK_MEMORY_UPPER_BOUND_MB, (
        f"Peak memory {result.peak_memory_mb:.1f} MB exceeded "
        f"{PEAK_MEMORY_UPPER_BOUND_MB} MB ceiling"
    )


@pytest.mark.slow
def test_memory_fields_on_infeasible() -> None:
    """Memory fields are present even when avoidance constraints cause infeasibility."""
    members = [
        TeamMember(
            name="Member000",
            timezone="UTC",
            avoid_buddies=["Member001", "Member002", "Member003"],
        ),
        TeamMember(name="Member001", timezone="UTC"),
        TeamMember(name="Member002", timezone="UTC"),
        TeamMember(name="Member003", timezone="UTC"),
    ]
    result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.OPTIMAL)

    assert not result.success
    assert result.peak_memory_mb is not None
    assert result.memory_delta_mb is not None
