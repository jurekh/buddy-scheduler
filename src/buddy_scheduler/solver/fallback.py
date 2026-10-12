"""Fallback pairing strategies for when the MIP solver fails."""

from __future__ import annotations

import logging
import random
import time

import psutil

from buddy_scheduler.models import OptimizationResult, PairingHistory, TeamMember
from buddy_scheduler.tz_utils import tz_penalty

logger = logging.getLogger(__name__)


def _compute_score(
    pairs: list[tuple[str, str]],
    history: PairingHistory | None,
    history_weight: float,
    tz_weight: float,
    tz_map: dict[str, str],
) -> float:
    """Return the total weighted penalty for a list of pairs."""
    score = 0.0
    for a, b in pairs:
        if history is not None and history_weight > 0.0:
            score += history_weight * history.get_pair_count(a, b)
        if tz_weight > 0.0:
            score += tz_weight * tz_penalty(tz_map[a], tz_map[b])
    return score


def greedy_min_penalty(
    members: list[TeamMember],
    history_weight: float,
    tz_weight: float,
    history: PairingHistory | None,
    avoidance_pairs: set[frozenset[str]],
    profile_name: str,
) -> OptimizationResult:
    """Greedy pairing: iteratively select the lowest-cost valid pair.

    Returns:
        OptimizationResult with success=True if a valid pairing is found,
        success=False otherwise.
    """
    start = time.monotonic()
    process = psutil.Process()
    rss_before = process.memory_info().rss

    active = [m for m in members if m.active]
    inactive_names = sorted(m.name for m in members if not m.active)
    n = len(active)

    if n < 2:
        return OptimizationResult(
            success=False,
            pairs=[],
            sitting_out=None,
            optimization_score=0.0,
            solve_time=time.monotonic() - start,
            solver_profile=f"{profile_name}_fallback_greedy_min_penalty",
            inactive_members=inactive_names,
            error="Fewer than 2 active members.",
        )

    names = [m.name for m in active]
    tz_map = {m.name: m.timezone for m in active}

    # Build sorted list of all valid (cost, i, j) pairs
    candidates: list[tuple[float, int, int]] = []
    for i in range(n):
        for j in range(i + 1, n):
            if frozenset({names[i], names[j]}) not in avoidance_pairs:
                cost = 0.0
                if history is not None and history_weight > 0.0:
                    cost += history_weight * history.get_pair_count(names[i], names[j])
                if tz_weight > 0.0:
                    cost += tz_weight * tz_penalty(tz_map[names[i]], tz_map[names[j]])
                candidates.append((cost, i, j))
    candidates.sort()

    # Greedy assignment
    paired: set[int] = set()
    result_pairs: list[tuple[str, str]] = []
    total_score = 0.0

    for cost, i, j in candidates:
        if i not in paired and j not in paired:
            result_pairs.append((names[i], names[j]))
            total_score += cost
            paired.add(i)
            paired.add(j)

    unpaired = [i for i in range(n) if i not in paired]
    odd = n % 2 == 1

    if odd and len(unpaired) == 1:
        sitting_out: str | None = names[unpaired[0]]
    elif not odd and len(unpaired) == 0:
        sitting_out = None
    else:
        rss_after = process.memory_info().rss
        return OptimizationResult(
            success=False,
            pairs=[],
            sitting_out=None,
            optimization_score=0.0,
            solve_time=time.monotonic() - start,
            solver_profile=f"{profile_name}_fallback_greedy_min_penalty",
            peak_memory_mb=rss_after / 1_048_576,
            memory_delta_mb=(rss_after - rss_before) / 1_048_576,
            inactive_members=inactive_names,
            error="Greedy pairing failed: could not pair all members.",
        )

    rss_after = process.memory_info().rss
    solve_time = time.monotonic() - start
    logger.info("Greedy fallback completed in %.3fs", solve_time)

    return OptimizationResult(
        success=True,
        pairs=result_pairs,
        sitting_out=sitting_out,
        optimization_score=total_score,
        solve_time=solve_time,
        solver_profile=f"{profile_name}_fallback_greedy_min_penalty",
        peak_memory_mb=rss_after / 1_048_576,
        memory_delta_mb=(rss_after - rss_before) / 1_048_576,
        inactive_members=inactive_names,
    )


def random_pairing(
    members: list[TeamMember],
    history_weight: float,
    tz_weight: float,
    history: PairingHistory | None,
    avoidance_pairs: set[frozenset[str]],
    profile_name: str,
) -> OptimizationResult:
    """Random pairing: shuffle members and pair sequentially, retrying on violations.

    Returns:
        OptimizationResult with success=True if a valid pairing is found within
        the retry budget, success=False otherwise.
    """
    start = time.monotonic()
    process = psutil.Process()
    rss_before = process.memory_info().rss

    active = [m for m in members if m.active]
    inactive_names = sorted(m.name for m in members if not m.active)
    n = len(active)

    if n < 2:
        return OptimizationResult(
            success=False,
            pairs=[],
            sitting_out=None,
            optimization_score=0.0,
            solve_time=time.monotonic() - start,
            solver_profile=f"{profile_name}_fallback_random",
            inactive_members=inactive_names,
            error="Fewer than 2 active members.",
        )

    names = [m.name for m in active]
    tz_map = {m.name: m.timezone for m in active}
    odd = n % 2 == 1
    max_retries = 200

    for _ in range(max_retries):
        shuffled = names.copy()
        random.shuffle(shuffled)

        sitting_out: str | None = shuffled[-1] if odd else None
        to_pair = shuffled[:-1] if odd else shuffled
        pairs = [(to_pair[k], to_pair[k + 1]) for k in range(0, len(to_pair), 2)]

        if all(frozenset({a, b}) not in avoidance_pairs for a, b in pairs):
            score = _compute_score(pairs, history, history_weight, tz_weight, tz_map)
            rss_after = process.memory_info().rss
            solve_time = time.monotonic() - start
            logger.info("Random fallback completed in %.3fs", solve_time)
            return OptimizationResult(
                success=True,
                pairs=pairs,
                sitting_out=sitting_out,
                optimization_score=score,
                solve_time=solve_time,
                solver_profile=f"{profile_name}_fallback_random",
                peak_memory_mb=rss_after / 1_048_576,
                memory_delta_mb=(rss_after - rss_before) / 1_048_576,
                inactive_members=inactive_names,
            )

    rss_after = process.memory_info().rss
    return OptimizationResult(
        success=False,
        pairs=[],
        sitting_out=None,
        optimization_score=0.0,
        solve_time=time.monotonic() - start,
        solver_profile=f"{profile_name}_fallback_random",
        peak_memory_mb=rss_after / 1_048_576,
        memory_delta_mb=(rss_after - rss_before) / 1_048_576,
        inactive_members=inactive_names,
        error="Random pairing failed: no valid pairing found within retry budget.",
    )


def round_robin_pairing(
    members: list[TeamMember],
    history_weight: float,
    tz_weight: float,
    history: PairingHistory | None,
    avoidance_pairs: set[frozenset[str]],
    profile_name: str,
) -> OptimizationResult:
    """Round-robin pairing: deterministic rotation-based pairing respecting avoidance.

    Returns:
        OptimizationResult with success=True if a valid pairing is found,
        success=False if all rotations are blocked by avoidance constraints.
    """
    start = time.monotonic()
    process = psutil.Process()
    rss_before = process.memory_info().rss

    active = [m for m in members if m.active]
    inactive_names = sorted(m.name for m in members if not m.active)
    n = len(active)

    if n < 2:
        return OptimizationResult(
            success=False,
            pairs=[],
            sitting_out=None,
            optimization_score=0.0,
            solve_time=time.monotonic() - start,
            solver_profile=f"{profile_name}_fallback_round_robin",
            inactive_members=inactive_names,
            error="Fewer than 2 active members.",
        )

    names = [m.name for m in active]
    tz_map = {m.name: m.timezone for m in active}
    odd = n % 2 == 1

    # Try all n rotations; first valid one wins
    for offset in range(n):
        rotated = names[offset:] + names[:offset]
        sitting_out: str | None = rotated[-1] if odd else None
        to_pair = rotated[:-1] if odd else rotated
        pairs = [(to_pair[k], to_pair[k + 1]) for k in range(0, len(to_pair), 2)]

        if all(frozenset({a, b}) not in avoidance_pairs for a, b in pairs):
            score = _compute_score(pairs, history, history_weight, tz_weight, tz_map)
            rss_after = process.memory_info().rss
            solve_time = time.monotonic() - start
            logger.info("Round-robin fallback completed in %.3fs", solve_time)
            return OptimizationResult(
                success=True,
                pairs=pairs,
                sitting_out=sitting_out,
                optimization_score=score,
                solve_time=solve_time,
                solver_profile=f"{profile_name}_fallback_round_robin",
                peak_memory_mb=rss_after / 1_048_576,
                memory_delta_mb=(rss_after - rss_before) / 1_048_576,
                inactive_members=inactive_names,
            )

    rss_after = process.memory_info().rss
    return OptimizationResult(
        success=False,
        pairs=[],
        sitting_out=None,
        optimization_score=0.0,
        solve_time=time.monotonic() - start,
        solver_profile=f"{profile_name}_fallback_round_robin",
        peak_memory_mb=rss_after / 1_048_576,
        memory_delta_mb=(rss_after - rss_before) / 1_048_576,
        inactive_members=inactive_names,
        error="Round-robin pairing failed: all rotations blocked by avoidance.",
    )
