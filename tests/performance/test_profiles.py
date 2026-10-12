"""Solver profile resolution and time-monotonicity regression tests.

Verifies that the adaptive profile logic resolves to the correct concrete
profile at every documented threshold boundary, and that solve time grows
monotonically with team size.

All tests are marked ``slow`` and excluded from the default ``pytest`` run.
Run explicitly with ``pytest -m slow tests/performance/test_profiles.py``.
"""

from __future__ import annotations

import pytest

from buddy_scheduler.solver.mip import solve_pairing
from buddy_scheduler.solver.profiles import SolverProfile

from .conftest import make_team


class TestAdaptiveProfileResolution:
    """Verify the adaptive profile resolves correctly at every threshold boundary.

    Thresholds (from profiles.py):
    - N ≤ 15  → "optimal"
    - 16 ≤ N ≤ 60 → "balanced"
    - N > 60  → "fast"
    """

    @pytest.mark.slow
    def test_n15_resolves_optimal(self) -> None:
        """N=15 (upper boundary of optimal range) → solver_profile == 'optimal'."""
        result = solve_pairing(
            make_team(15), 0.0, 0.0, None, set(), SolverProfile.ADAPTIVE
        )
        assert result.success
        assert result.solver_profile == "optimal"

    @pytest.mark.slow
    def test_n16_resolves_balanced(self) -> None:
        """N=16 (lower boundary of balanced range) → solver_profile == 'balanced'."""
        result = solve_pairing(
            make_team(16), 0.0, 0.0, None, set(), SolverProfile.ADAPTIVE
        )
        assert result.success
        assert result.solver_profile == "balanced"

    @pytest.mark.slow
    def test_n60_resolves_balanced(self) -> None:
        """N=60 (upper boundary of balanced range) → solver_profile == 'balanced'."""
        result = solve_pairing(
            make_team(60), 0.0, 0.0, None, set(), SolverProfile.ADAPTIVE
        )
        assert result.success
        assert result.solver_profile == "balanced"

    @pytest.mark.slow
    def test_n61_resolves_fast(self) -> None:
        """N=61 (lower boundary of fast range) → solver_profile == 'fast'."""
        result = solve_pairing(
            make_team(61), 0.0, 0.0, None, set(), SolverProfile.ADAPTIVE
        )
        assert result.success
        assert result.solver_profile == "fast"

    @pytest.mark.slow
    def test_n100_resolves_fast(self) -> None:
        """N=100 (well inside fast range) → solver_profile == 'fast'."""
        result = solve_pairing(
            make_team(100), 0.0, 0.0, None, set(), SolverProfile.ADAPTIVE
        )
        assert result.success
        assert result.solver_profile == "fast"


class TestSolveTimeMonotonicity:
    """Solve time should not decrease as team size grows."""

    @pytest.mark.slow
    def test_monotonic_10_20_30(self) -> None:
        """solve_time(N=30) >= solve_time(N=10) using solver-reported time."""
        results = [
            solve_pairing(
                make_team(n), 0.0, 0.0, None, set(), SolverProfile.ADAPTIVE
            )
            for n in (10, 20, 30)
        ]
        for r in results:
            assert r.success

        # Use result.solve_time (solver-reported) to avoid Python startup overhead
        # skewing very fast small-team solves.
        assert results[2].solve_time >= results[0].solve_time, (
            f"solve_time(N=30)={results[2].solve_time:.4f}s < "
            f"solve_time(N=10)={results[0].solve_time:.4f}s"
        )


class TestExplicitProfiles:
    """Every named profile produces a valid result on a medium-sized team."""

    @pytest.mark.slow
    def test_all_explicit_profiles_succeed(self) -> None:
        """fast, balanced, and optimal profiles all succeed on N=20."""
        for profile in (
            SolverProfile.FAST, SolverProfile.BALANCED, SolverProfile.OPTIMAL
        ):
            result = solve_pairing(
                make_team(20), 0.0, 0.0, None, set(), profile
            )
            assert result.success, f"Profile {profile.value} failed on N=20"
            assert result.solver_profile == profile.value
