"""Multi-round fairness analysis tests for the buddy-pairing solver.

Simulates consecutive scheduling rounds and asserts that pairings are
distributed equitably over time, measured by pairwise standard deviation
and sit-out spread.

All tests are marked ``slow`` and excluded from the default ``pytest`` run.
Run explicitly with ``pytest -m slow tests/performance/test_fairness.py``.
"""

from __future__ import annotations

import statistics

import pytest

from buddy_scheduler.models import PairingHistory

from .conftest import TIMEZONES, make_team, simulate_rounds


def _pairwise_counts(history: PairingHistory, member_names: list[str]) -> list[int]:
    """Return the meeting count for every unique pair in *member_names*.

    Args:
        history: Accumulated pairing history after all rounds.
        member_names: Ordered list of member names to enumerate.

    Returns:
        A list of non-negative integers, one per unique (i, j) pair where i < j.
    """
    counts: list[int] = []
    for i, a in enumerate(member_names):
        for b in member_names[i + 1 :]:
            counts.append(history.get_pair_count(a, b))
    return counts


@pytest.mark.slow
def test_pairwise_stdev_10_members() -> None:
    """15 rounds on a 10-member team: pairwise std-dev ≤ 0.5 and max-gap ≤ 1.

    With 10 members and 15 rounds there are 45 unique pairs and 75 pair-slots
    (15 rounds × 5 pairs/round), so the expected mean is 1.667 meetings/pair.
    Because counts are integers, the minimum achievable std-dev is
    √(2/3 × 1/3) ≈ 0.471 (30 pairs at 2, 15 pairs at 1).  The solver reaches
    this theoretical minimum, so the threshold is set to 0.5.
    """
    members = make_team(10)
    history = simulate_rounds(members, 15, 1.0, 0.0)

    names = [m.name for m in members]
    counts = _pairwise_counts(history, names)

    stdev = statistics.pstdev(counts)
    max_gap = max(counts) - min(counts)

    assert stdev <= 0.5, (
        f"Pairwise std-dev {stdev:.3f} exceeds 0.5 after 15 rounds (N=10)"
    )
    assert max_gap <= 1, (
        f"Pairwise max-gap {max_gap} exceeds 1 after 15 rounds (N=10)"
    )


@pytest.mark.slow
def test_pairwise_stdev_20_members() -> None:
    """10 rounds on a 20-member team: pairwise std-dev ≤ 0.5.

    With 20 members and 10 rounds there are 190 unique pairs and 100 pair-slots
    (10 rounds × 10 pairs/round), so the expected mean is 0.526 meetings/pair.
    All counts are 0 or 1, giving minimum achievable std-dev of
    √(0.526 × 0.474) ≈ 0.499.  The solver reaches this theoretical minimum,
    so the threshold is set to 0.5.
    """
    members = make_team(20)
    history = simulate_rounds(members, 10, 1.0, 0.0)

    names = [m.name for m in members]
    counts = _pairwise_counts(history, names)

    stdev = statistics.pstdev(counts)

    assert stdev <= 0.5, (
        f"Pairwise std-dev {stdev:.3f} exceeds 0.5 after 10 rounds (N=20)"
    )


@pytest.mark.slow
def test_sitout_rotation_11_members() -> None:
    """11 rounds on an 11-member team: no member sits out more than twice."""
    members = make_team(11)
    history = simulate_rounds(members, 11, 1.0, 0.0)

    assert len(history.sit_out_counts) > 0, "No sit-out counts recorded"
    sit_out_max = max(history.sit_out_counts.values())
    assert sit_out_max <= 2, (
        f"Max sit-out count {sit_out_max} exceeds 2 after 11 rounds (N=11); "
        f"distribution: {history.sit_out_counts}"
    )


@pytest.mark.slow
def test_cross_tz_pairings_occur() -> None:
    """10 rounds on a 12-member / 2-timezone team: cross-group pairings appear."""
    members = make_team(12, tz_count=2)
    # Members 0-5 → TIMEZONES[0], members 6-11 → TIMEZONES[1]
    tz_a = TIMEZONES[0]
    tz_b = TIMEZONES[1]

    group_a = [m.name for m in members if m.timezone == tz_a]
    group_b = [m.name for m in members if m.timezone == tz_b]

    history = simulate_rounds(members, 10, 1.0, 0.0)

    cross_pairings = sum(
        history.get_pair_count(a, b) for a in group_a for b in group_b
    )
    assert cross_pairings > 0, (
        "No cross-timezone pairings occurred after 10 rounds; "
        "history-weight should diversify pairings beyond timezone groups"
    )


@pytest.mark.slow
def test_zero_history_weight_no_fairness_required() -> None:
    """5 rounds with history_weight=0 complete without error; no distribution asserted.

    This test documents the precondition: fairness is a consequence of the
    history penalty weight.  With weight=0 the solver has no incentive to
    avoid repeated pairs, so no std-dev assertion is made.
    """
    members = make_team(10)
    # history_weight=0 → fairness not guaranteed; this test documents the precondition
    simulate_rounds(members, 5, 0.0, 0.0)
    # If we reach here, all 5 rounds succeeded — that's the only requirement.
