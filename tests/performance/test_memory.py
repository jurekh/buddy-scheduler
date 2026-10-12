"""Memory metric tests for the buddy-pairing solver.

Verifies that ``peak_memory_mb`` and ``memory_delta_mb`` are populated,
non-negative, and scale with team size.

``peak_memory_mb`` is the absolute process RSS after the solve; its value
depends on how much memory the process had already allocated from prior test
runs.  ``memory_delta_mb`` is the incremental RSS change caused by the solve
itself and is test-order-independent, so it is used for the upper-bound
assertion.

All tests are marked ``slow`` and excluded from the default ``pytest`` run.
Run explicitly with ``pytest -m slow tests/performance/test_memory.py``.
"""

from __future__ import annotations

import pytest

from buddy_scheduler.models import PairingHistory, TeamMember
from buddy_scheduler.solver.mip import solve_pairing
from buddy_scheduler.solver.profiles import SolverProfile

from .conftest import make_team

# Measured memory_delta_mb at 0.66–0.89 MB on a 50-member full-history run.
# 5 MB gives ~6× headroom for GC variance and is test-order-independent because
# it measures incremental solver allocation, not absolute process RSS.
MEMORY_DELTA_UPPER_BOUND_MB: float = 5.0


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
def test_memory_delta_upper_bound_50_members() -> None:
    """Solver memory delta stays below 5 MB for a 50-member team with a full history.

    ``memory_delta_mb`` measures incremental RSS change caused by the solve
    itself (rss_after - rss_before inside the solver), so it is independent of
    how much memory prior tests have already allocated in the process.
    Measured at 0.66–0.89 MB; the 5 MB ceiling gives ~6× headroom.
    """
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
    assert result.memory_delta_mb is not None
    assert result.memory_delta_mb < MEMORY_DELTA_UPPER_BOUND_MB, (
        f"Memory delta {result.memory_delta_mb:.2f} MB exceeded "
        f"{MEMORY_DELTA_UPPER_BOUND_MB} MB ceiling"
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
