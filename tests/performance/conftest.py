"""Shared helpers for performance and fairness tests."""

from __future__ import annotations

from buddy_scheduler.models import PairingHistory, TeamMember
from buddy_scheduler.solver.mip import solve_pairing
from buddy_scheduler.solver.profiles import SolverProfile

TIMEZONES: list[str] = [
    "UTC",
    "America/New_York",
    "Europe/London",
    "Asia/Tokyo",
    "America/Los_Angeles",
    "Asia/Kolkata",
]


def make_team(n: int, tz_count: int = 6) -> list[TeamMember]:
    """Build a deterministic synthetic team of *n* active members.

    Names follow the pattern ``Member000``, ``Member001``, … and timezones cycle
    through the first *tz_count* entries of :data:`TIMEZONES`.  All members are
    active with no avoidance constraints, so the team is reproducible across runs
    without any RNG seed management.

    Args:
        n: Number of active team members to generate (must be ≥ 0).
        tz_count: How many distinct timezones to cycle through (1–6).

    Returns:
        A list of :class:`TeamMember` instances.
    """
    effective_tz_count = min(tz_count, len(TIMEZONES))
    return [
        TeamMember(
            name=f"Member{i:03d}",
            timezone=TIMEZONES[i % effective_tz_count],
        )
        for i in range(n)
    ]


def simulate_rounds(
    members: list[TeamMember],
    n_rounds: int,
    history_weight: float,
    tz_weight: float,
    profile: SolverProfile = SolverProfile.ADAPTIVE,
) -> PairingHistory:
    """Run *n_rounds* consecutive scheduling rounds, updating history after each.

    Each round calls :func:`solve_pairing` with the same members and mutates a
    shared :class:`PairingHistory` in place using the public
    :meth:`~PairingHistory.increment_pair` and
    :meth:`~PairingHistory.increment_sit_out` methods.  This mirrors exactly
    what the production CLI does, satisfying FR-012.

    Args:
        members: Team roster passed unchanged to every round.
        n_rounds: Number of scheduling rounds to simulate.
        history_weight: Weight applied to historical pairing penalties.
        tz_weight: Weight applied to timezone incompatibility penalties.
        profile: Solver profile to use (default: ADAPTIVE).

    Returns:
        The accumulated :class:`PairingHistory` after all rounds complete.

    Raises:
        AssertionError: If any individual round returns ``success=False``.
    """
    history = PairingHistory()
    for round_index in range(n_rounds):
        result = solve_pairing(
            members,
            history_weight,
            tz_weight,
            history,
            set(),
            profile,
        )
        assert result.success, (
            f"Round {round_index + 1}/{n_rounds} failed: {result.error}"
        )
        for a, b in result.pairs:
            history.increment_pair(a, b)
        if result.sitting_out is not None:
            history.increment_sit_out(result.sitting_out)
    return history
