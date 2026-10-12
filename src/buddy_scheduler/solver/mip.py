"""MIP-based buddy pairing solver using PuLP/CBC."""

from __future__ import annotations

import logging
import time

import psutil
import pulp

from buddy_scheduler.models import (
    OptimizationError,
    OptimizationResult,
    PairingHistory,
    TeamMember,
)
from buddy_scheduler.solver.profiles import SolverProfile, get_profile_config
from buddy_scheduler.tz_utils import tz_penalty

logger = logging.getLogger(__name__)


def _resolve_profile_name(profile: SolverProfile, n_active: int) -> str:
    """Return the concrete profile name after resolving ADAPTIVE."""
    if profile is SolverProfile.ADAPTIVE:
        if n_active <= 15:
            return str(SolverProfile.OPTIMAL.value)
        if n_active <= 60:
            return str(SolverProfile.BALANCED.value)
        return str(SolverProfile.FAST.value)
    return str(profile.value)


def _compute_avoidance_conflicts(
    active: list[TeamMember], avoidance_pairs: set[frozenset[str]]
) -> list[str]:
    """Return descriptions of active members with no eligible pairing partners."""
    active_names = {m.name for m in active}
    conflicts: list[str] = []
    for m in active:
        eligible = {
            other
            for other in active_names
            if other != m.name and frozenset({m.name, other}) not in avoidance_pairs
        }
        if not eligible:
            conflicts.append(f"{m.name} has no eligible pairing partners")
    return conflicts


def solve_pairing(
    members: list[TeamMember],
    history_weight: float,
    tz_weight: float,
    history: PairingHistory | None,
    avoidance_pairs: set[frozenset[str]],
    profile: SolverProfile,
) -> OptimizationResult:
    """Solve the buddy pairing problem using MIP.

    Args:
        members: Full team roster (active and inactive).
        history_weight: Weight applied to historical pairing penalties.
        tz_weight: Weight applied to timezone incompatibility penalties.
        history: Optional pairing history for weighted objective.
        avoidance_pairs: Explicit set of forbidden pair frozensets.
        profile: Solver profile to use.

    Returns:
        An OptimizationResult describing the pairing outcome.

    Raises:
        OptimizationError: When MIP fails and all fallback strategies are exhausted.
    """
    inactive = [m for m in members if not m.active]
    active = [m for m in members if m.active]
    inactive_names = sorted(m.name for m in inactive)

    n = len(active)
    resolved_profile_name = _resolve_profile_name(profile, n)

    if n < 2:
        return OptimizationResult(
            success=False,
            pairs=[],
            sitting_out=None,
            optimization_score=0.0,
            solve_time=0.0,
            solver_profile=resolved_profile_name,
            inactive_members=inactive_names,
            error="Fewer than 2 active members; pairing is not possible.",
        )

    # Build complete avoidance set: passed parameter + member avoid_buddies (symmetric)
    active_names_set = {m.name for m in active}
    member_avoidance: set[frozenset[str]] = {
        frozenset({m.name, buddy})
        for m in members
        for buddy in m.avoid_buddies
        if buddy in active_names_set and m.name in active_names_set
    }
    all_avoidance = avoidance_pairs | member_avoidance

    names = [m.name for m in active]
    tz_map = {m.name: m.timezone for m in active}
    odd = n % 2 == 1

    config = get_profile_config(profile, n)
    logger.info(
        "Starting MIP solve: %d active members, profile=%s", n, resolved_profile_name
    )

    prob = pulp.LpProblem("buddy_pairing", pulp.LpMinimize)

    # Binary pair variables x[i,j] for i < j, excluding avoidance pairs
    x: dict[tuple[int, int], pulp.LpVariable] = {}
    for i in range(n):
        for j in range(i + 1, n):
            if frozenset({names[i], names[j]}) not in all_avoidance:
                x[i, j] = pulp.LpVariable(f"x_{i}_{j}", cat="Binary")

    # Binary sit-out variables s[i] (only for odd N)
    s: dict[int, pulp.LpVariable] = {}
    if odd:
        for i in range(n):
            s[i] = pulp.LpVariable(f"s_{i}", cat="Binary")

    # Coverage constraints: each active member paired exactly once (or sits out)
    for i in range(n):
        pairs_for_i = [var for (k, m), var in x.items() if k == i or m == i]
        if odd:
            prob += pulp.lpSum(pairs_for_i) + s[i] == 1, f"cover_{i}"
        else:
            prob += pulp.lpSum(pairs_for_i) == 1, f"cover_{i}"

    # Exactly one person sits out for odd N
    if odd:
        prob += pulp.lpSum(s.values()) == 1, "sit_out_total"

    # Objective: minimise weighted penalty sum
    objective_terms: list[pulp.LpAffineExpression] = []
    for (i, j), var in x.items():
        cost = 0.0
        if history is not None and history_weight > 0.0:
            cost += history_weight * history.get_pair_count(names[i], names[j])
        if tz_weight > 0.0:
            cost += tz_weight * tz_penalty(tz_map[names[i]], tz_map[names[j]])
        objective_terms.append(cost * var)

    # Sit-out fairness: prefer least-sat-out member to sit out
    if odd and history is not None:
        for i, var in s.items():
            sit_cost = float(history.sit_out_counts.get(names[i], 0))
            objective_terms.append(sit_cost * var)

    prob += pulp.lpSum(objective_terms)

    # Memory tracking
    process = psutil.Process()
    rss_before = process.memory_info().rss

    start_time = time.monotonic()
    solver = pulp.PULP_CBC_CMD(
        msg=0,
        gapRel=config.gap_tolerance,
        timeLimit=config.time_limit_s,
        options=config.cbc_options if config.cbc_options else [],
    )
    status = prob.solve(solver)
    solve_time = time.monotonic() - start_time

    rss_after = process.memory_info().rss
    peak_memory_mb = rss_after / 1_048_576
    memory_delta_mb = (rss_after - rss_before) / 1_048_576

    logger.info(
        "Solved in %.3fs, peak memory %.1f MB", solve_time, peak_memory_mb
    )

    if status == pulp.constants.LpStatusOptimal:
        result_pairs: list[tuple[str, str]] = []
        sitting_out: str | None = None
        score = 0.0

        for (i, j), var in x.items():
            val = pulp.value(var)
            if val is not None and val > 0.5:
                result_pairs.append((names[i], names[j]))
                if history is not None and history_weight > 0.0:
                    score += history_weight * history.get_pair_count(names[i], names[j])
                if tz_weight > 0.0:
                    score += tz_weight * tz_penalty(tz_map[names[i]], tz_map[names[j]])

        if odd:
            for i, var in s.items():
                val = pulp.value(var)
                if val is not None and val > 0.5:
                    sitting_out = names[i]

        return OptimizationResult(
            success=True,
            pairs=result_pairs,
            sitting_out=sitting_out,
            optimization_score=score,
            solve_time=solve_time,
            solver_profile=resolved_profile_name,
            peak_memory_mb=peak_memory_mb,
            memory_delta_mb=memory_delta_mb,
            inactive_members=inactive_names,
        )

    if status == pulp.constants.LpStatusInfeasible:
        avoidance_conflicts = _compute_avoidance_conflicts(active, all_avoidance)
        return OptimizationResult(
            success=False,
            pairs=[],
            sitting_out=None,
            optimization_score=0.0,
            solve_time=solve_time,
            solver_profile=resolved_profile_name,
            peak_memory_mb=peak_memory_mb,
            memory_delta_mb=memory_delta_mb,
            inactive_members=inactive_names,
            avoidance_conflicts=avoidance_conflicts,
            error="Infeasible: avoidance constraints prevent a valid pairing.",
        )

    # Solver failure — attempt fallback chain
    status_str = pulp.constants.LpStatus.get(status, str(status))
    logger.warning(
        "MIP solver returned status %s, attempting fallback: greedy", status_str
    )

    from buddy_scheduler.solver.fallback import (  # noqa: PLC0415
        greedy_min_penalty,
        random_pairing,
        round_robin_pairing,
    )

    result = greedy_min_penalty(
        members=members,
        history_weight=history_weight,
        tz_weight=tz_weight,
        history=history,
        avoidance_pairs=all_avoidance,
        profile_name=resolved_profile_name,
    )
    if result.success:
        return result

    logger.warning("greedy failed, attempting fallback: random")
    result = random_pairing(
        members=members,
        history_weight=history_weight,
        tz_weight=tz_weight,
        history=history,
        avoidance_pairs=all_avoidance,
        profile_name=resolved_profile_name,
    )
    if result.success:
        return result

    logger.warning("random failed, attempting fallback: round_robin")
    result = round_robin_pairing(
        members=members,
        history_weight=history_weight,
        tz_weight=tz_weight,
        history=history,
        avoidance_pairs=all_avoidance,
        profile_name=resolved_profile_name,
    )
    if result.success:
        return result

    raise OptimizationError("All fallback strategies exhausted")
