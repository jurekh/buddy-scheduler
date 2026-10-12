"""Unit tests for the MIP solver core."""

from __future__ import annotations

import pytest

from buddy_scheduler.models import PairingHistory, TeamMember
from buddy_scheduler.solver.mip import solve_pairing
from buddy_scheduler.solver.profiles import SolverProfile


def _make_members(names: list[str], tz: str = "UTC") -> list[TeamMember]:
    return [TeamMember(name=n, timezone=tz) for n in names]


class TestBasicPairing:
    """T012: Core MIP solver without penalties."""

    def test_even_n_all_members_paired(self) -> None:
        members = _make_members(["Alice", "Bob", "Charlie", "Dave"])
        result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.OPTIMAL)

        assert result.success
        all_paired = {name for pair in result.pairs for name in pair}
        assert all_paired == {"Alice", "Bob", "Charlie", "Dave"}
        assert len(result.pairs) == 2
        assert result.sitting_out is None

    def test_even_n_no_member_appears_twice(self) -> None:
        members = _make_members(["Alice", "Bob", "Charlie", "Dave"])
        result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.OPTIMAL)

        all_names = [name for pair in result.pairs for name in pair]
        assert len(all_names) == len(set(all_names))

    def test_odd_n_one_sits_out(self) -> None:
        members = _make_members(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.OPTIMAL)

        assert result.success
        assert result.sitting_out is not None
        assert result.sitting_out in {m.name for m in members}
        assert len(result.pairs) == 2
        paired_names = {name for pair in result.pairs for name in pair}
        assert result.sitting_out not in paired_names

    def test_fewer_than_two_active_returns_failure_one_active(self) -> None:
        members = [
            TeamMember(name="Alice", timezone="UTC"),
            TeamMember(name="Bob", timezone="UTC", active=False),
        ]
        result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.OPTIMAL)

        assert not result.success
        assert result.pairs == []
        assert "Fewer than 2" in (result.error or "")

    def test_fewer_than_two_active_returns_failure_zero_active(self) -> None:
        members = [
            TeamMember(name="Alice", timezone="UTC", active=False),
        ]
        result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.OPTIMAL)

        assert not result.success

    def test_inactive_member_never_appears_in_pairs(self) -> None:
        members = [
            TeamMember(name="Alice", timezone="UTC"),
            TeamMember(name="Bob", timezone="UTC"),
            TeamMember(name="Charlie", timezone="UTC", active=False),
            TeamMember(name="Dave", timezone="UTC"),
        ]
        result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.OPTIMAL)

        assert result.success
        all_names = {name for pair in result.pairs for name in pair}
        assert "Charlie" not in all_names
        assert "Charlie" in result.inactive_members

    def test_solve_time_positive(self) -> None:
        members = _make_members(["Alice", "Bob", "Charlie", "Dave"])
        result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.OPTIMAL)

        assert result.solve_time > 0

    def test_solver_profile_resolved_not_adaptive(self) -> None:
        members = _make_members(["A", "B", "C", "D"])
        result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.ADAPTIVE)

        assert result.solver_profile != "adaptive"
        assert result.solver_profile in {"optimal", "balanced", "fast"}

    def test_solver_profile_fast_preserved(self) -> None:
        members = _make_members(["A", "B", "C", "D"])
        result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.FAST)

        assert result.solver_profile == "fast"

    def test_memory_fields_present(self) -> None:
        members = _make_members(["Alice", "Bob", "Charlie", "Dave"])
        result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.OPTIMAL)

        assert result.peak_memory_mb is not None
        assert result.peak_memory_mb > 0
        assert result.memory_delta_mb is not None

    def test_two_active_members_one_pair(self) -> None:
        members = _make_members(["Alice", "Bob"])
        result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.OPTIMAL)

        assert result.success
        assert len(result.pairs) == 1
        assert set(result.pairs[0]) == {"Alice", "Bob"}


class TestHistoryPenalty:
    """T021: History penalty drives the solver away from repeated pairs."""

    def test_high_history_weight_avoids_repeated_pair(self) -> None:
        members = _make_members(["Alice", "Bob", "Charlie", "Dave"])
        history = PairingHistory()
        # Alice and Bob have been paired many times
        for _ in range(10):
            history.increment_pair("Alice", "Bob")

        result = solve_pairing(
            members, 5.0, 0.0, history, set(), SolverProfile.OPTIMAL
        )

        assert result.success
        paired_pairs = [frozenset(p) for p in result.pairs]
        assert frozenset({"Alice", "Bob"}) not in paired_pairs

    def test_history_weight_zero_ignores_history(self) -> None:
        """With history_weight=0 the solver ignores pair counts."""
        members = _make_members(["Alice", "Bob", "Charlie", "Dave"])
        history = PairingHistory()
        for _ in range(100):
            history.increment_pair("Alice", "Bob")

        # With weight=0 the solver may still pair Alice-Bob (no penalty)
        result = solve_pairing(
            members, 0.0, 0.0, history, set(), SolverProfile.OPTIMAL
        )
        assert result.success
        assert len(result.pairs) == 2


class TestTimezonePenalty:
    """T025: Timezone penalty drives pairings within timezone groups."""

    def test_high_tz_weight_groups_by_timezone(self) -> None:
        members = [
            TeamMember(name="Alice", timezone="UTC"),
            TeamMember(name="Bob", timezone="UTC"),
            TeamMember(name="Charlie", timezone="America/New_York"),
            TeamMember(name="Dave", timezone="America/New_York"),
        ]
        result = solve_pairing(
            members, 0.0, 10.0, None, set(), SolverProfile.OPTIMAL
        )

        assert result.success
        paired_sets = [frozenset(p) for p in result.pairs]
        assert frozenset({"Alice", "Bob"}) in paired_sets
        assert frozenset({"Charlie", "Dave"}) in paired_sets


class TestAvoidanceConstraints:
    """T026: Avoidance constraints and infeasibility detection."""

    def test_avoidance_pair_excluded_from_result(self) -> None:
        members = [
            TeamMember(name="Alice", timezone="UTC", avoid_buddies=["Bob"]),
            TeamMember(name="Bob", timezone="UTC"),
            TeamMember(name="Charlie", timezone="UTC"),
            TeamMember(name="Dave", timezone="UTC"),
        ]
        result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.OPTIMAL)

        assert result.success
        paired_sets = [frozenset(p) for p in result.pairs]
        assert frozenset({"Alice", "Bob"}) not in paired_sets

    def test_avoidance_symmetric(self) -> None:
        """B lists A in avoid_buddies → pair A-B still excluded."""
        members = [
            TeamMember(name="Alice", timezone="UTC"),
            TeamMember(name="Bob", timezone="UTC", avoid_buddies=["Alice"]),
            TeamMember(name="Charlie", timezone="UTC"),
            TeamMember(name="Dave", timezone="UTC"),
        ]
        result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.OPTIMAL)

        assert result.success
        paired_sets = [frozenset(p) for p in result.pairs]
        assert frozenset({"Alice", "Bob"}) not in paired_sets

    def test_infeasible_avoidance_returns_failure(self) -> None:
        """A avoids everyone → infeasible even-N team."""
        members = [
            TeamMember(
                name="Alice",
                timezone="UTC",
                avoid_buddies=["Bob", "Charlie", "Dave"],
            ),
            TeamMember(name="Bob", timezone="UTC"),
            TeamMember(name="Charlie", timezone="UTC"),
            TeamMember(name="Dave", timezone="UTC"),
        ]
        result = solve_pairing(members, 0.0, 0.0, None, set(), SolverProfile.OPTIMAL)

        assert not result.success
        assert len(result.avoidance_conflicts) > 0
        assert any("Alice" in c for c in result.avoidance_conflicts)

    def test_explicit_avoidance_pairs_parameter(self) -> None:
        members = _make_members(["Alice", "Bob", "Charlie", "Dave"])
        explicit = {frozenset({"Alice", "Bob"})}
        result = solve_pairing(
            members, 0.0, 0.0, None, explicit, SolverProfile.OPTIMAL
        )

        assert result.success
        paired_sets = [frozenset(p) for p in result.pairs]
        assert frozenset({"Alice", "Bob"}) not in paired_sets

    @pytest.mark.slow
    def test_performance_100_members(self) -> None:
        """SC-004: N=100 active members must solve in < 5 seconds."""
        import random
        import time

        rng = random.Random(42)
        tzs = ["UTC", "America/New_York", "Europe/London", "Asia/Tokyo"]
        members = [
            TeamMember(name=f"Member{i:03d}", timezone=rng.choice(tzs))
            for i in range(100)
        ]
        start = time.monotonic()
        result = solve_pairing(members, 1.0, 1.0, None, set(), SolverProfile.ADAPTIVE)
        elapsed = time.monotonic() - start

        assert result.success
        assert elapsed < 5.0
