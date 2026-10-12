"""Wall-clock timing tests for the buddy-pairing solver across team-size bands.

All tests are marked ``slow`` and excluded from the default ``pytest`` run.
Run explicitly with ``pytest -m slow tests/performance/test_timing.py``.

Thresholds are derived from observed solve times in the reference
implementation with a 2× safety margin for CI hardware variance.
"""

from __future__ import annotations

import time

import pytest

from buddy_scheduler.models import PairingHistory
from buddy_scheduler.solver.mip import solve_pairing
from buddy_scheduler.solver.profiles import SolverProfile

from .conftest import make_team

# ---------------------------------------------------------------------------
# Per-size thresholds (seconds)
# ---------------------------------------------------------------------------

SMALL_THRESHOLD_S: float = 30.0  # N ≤ 15  → optimal profile
MEDIUM_THRESHOLD_S: float = 10.0  # N = 30  → balanced profile
MEDIUM_ODD_THRESHOLD_S: float = 15.0  # N = 35  → balanced profile, odd
LARGE_ODD_THRESHOLD_S: float = 10.0  # N = 25  → balanced profile, odd
LARGE_THRESHOLD_S: float = 30.0  # N = 50  → balanced profile
VERY_LARGE_THRESHOLD_S: float = 5.0  # N = 100 → fast profile
DENSE_HISTORY_THRESHOLD_S: float = 10.0  # N = 20 with full history matrix


# ---------------------------------------------------------------------------
# Small teams (N ≤ 15 → adaptive resolves to optimal)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_small_even_timing() -> None:
    """N=10 even team solves within SMALL_THRESHOLD_S using adaptive profile."""
    members = make_team(10)
    start = time.monotonic()
    result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.ADAPTIVE)
    elapsed = time.monotonic() - start

    assert result.success
    assert len(result.pairs) == 5
    assert result.sitting_out is None
    assert elapsed < SMALL_THRESHOLD_S, (
        f"N=10 solve took {elapsed:.2f}s, threshold {SMALL_THRESHOLD_S}s"
    )


@pytest.mark.slow
def test_small_odd_timing() -> None:
    """N=11 odd team solves within SMALL_THRESHOLD_S; exactly one member sits out."""
    members = make_team(11)
    start = time.monotonic()
    result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.ADAPTIVE)
    elapsed = time.monotonic() - start

    assert result.success
    assert result.sitting_out is not None
    assert len(result.pairs) == 5
    assert elapsed < SMALL_THRESHOLD_S, (
        f"N=11 solve took {elapsed:.2f}s, threshold {SMALL_THRESHOLD_S}s"
    )


# ---------------------------------------------------------------------------
# Medium teams (16 ≤ N ≤ 60 → adaptive resolves to balanced)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_medium_even_timing() -> None:
    """N=30 even team solves within MEDIUM_THRESHOLD_S using adaptive profile."""
    members = make_team(30)
    start = time.monotonic()
    result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.ADAPTIVE)
    elapsed = time.monotonic() - start

    assert result.success
    assert len(result.pairs) == 15
    assert result.sitting_out is None
    assert elapsed < MEDIUM_THRESHOLD_S, (
        f"N=30 solve took {elapsed:.2f}s, threshold {MEDIUM_THRESHOLD_S}s"
    )


@pytest.mark.slow
def test_medium_odd_timing() -> None:
    """N=35 odd team solves within MEDIUM_ODD_THRESHOLD_S; one member sits out."""
    members = make_team(35)
    start = time.monotonic()
    result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.ADAPTIVE)
    elapsed = time.monotonic() - start

    assert result.success
    assert result.sitting_out is not None
    assert len(result.pairs) == 17
    assert elapsed < MEDIUM_ODD_THRESHOLD_S, (
        f"N=35 solve took {elapsed:.2f}s, threshold {MEDIUM_ODD_THRESHOLD_S}s"
    )


# ---------------------------------------------------------------------------
# Large teams (still ≤ 60 → balanced; N=25 odd)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_large_odd_timing() -> None:
    """N=25 odd team solves within LARGE_ODD_THRESHOLD_S; one member sits out."""
    members = make_team(25)
    start = time.monotonic()
    result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.ADAPTIVE)
    elapsed = time.monotonic() - start

    assert result.success
    assert result.sitting_out is not None
    assert len(result.pairs) == 12
    assert elapsed < LARGE_ODD_THRESHOLD_S, (
        f"N=25 solve took {elapsed:.2f}s, threshold {LARGE_ODD_THRESHOLD_S}s"
    )


@pytest.mark.slow
def test_large_even_timing() -> None:
    """N=50 even team solves within LARGE_THRESHOLD_S using adaptive profile."""
    members = make_team(50)
    start = time.monotonic()
    result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.ADAPTIVE)
    elapsed = time.monotonic() - start

    assert result.success
    assert len(result.pairs) == 25
    assert result.sitting_out is None
    assert elapsed < LARGE_THRESHOLD_S, (
        f"N=50 solve took {elapsed:.2f}s, threshold {LARGE_THRESHOLD_S}s"
    )


# ---------------------------------------------------------------------------
# Very large team (N > 60 → adaptive resolves to fast)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_very_large_even_timing() -> None:
    """N=100 team solves within VERY_LARGE_THRESHOLD_S (fast profile auto-selected)."""
    members = make_team(100)
    start = time.monotonic()
    result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.ADAPTIVE)
    elapsed = time.monotonic() - start

    assert result.success
    assert len(result.pairs) == 50
    assert result.sitting_out is None
    assert elapsed < VERY_LARGE_THRESHOLD_S, (
        f"N=100 solve took {elapsed:.2f}s, threshold {VERY_LARGE_THRESHOLD_S}s"
    )


# ---------------------------------------------------------------------------
# Dense history
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_dense_history_timing() -> None:
    """N=20 team with full prior history solves within DENSE_HISTORY_THRESHOLD_S."""
    n = 20
    members = make_team(n)
    history = PairingHistory()
    names = [m.name for m in members]
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            history.increment_pair(a, b)

    start = time.monotonic()
    result = solve_pairing(members, 1.0, 0.0, history, set(), SolverProfile.ADAPTIVE)
    elapsed = time.monotonic() - start

    assert result.success
    assert len(result.pairs) == n // 2
    assert elapsed < DENSE_HISTORY_THRESHOLD_S, (
        f"N=20 dense-history solve took {elapsed:.2f}s, "
        f"threshold {DENSE_HISTORY_THRESHOLD_S}s"
    )


# ---------------------------------------------------------------------------
# Helpers (used by TeamMember construction outside conftest)
# ---------------------------------------------------------------------------

__all__ = [
    "SMALL_THRESHOLD_S",
    "MEDIUM_THRESHOLD_S",
    "MEDIUM_ODD_THRESHOLD_S",
    "LARGE_ODD_THRESHOLD_S",
    "LARGE_THRESHOLD_S",
    "VERY_LARGE_THRESHOLD_S",
    "DENSE_HISTORY_THRESHOLD_S",
]
