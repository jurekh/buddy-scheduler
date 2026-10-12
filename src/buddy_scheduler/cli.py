"""Command-line interface for buddy-scheduler."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click

from buddy_scheduler.models import (
    BuddySchedulerError,
    DataValidationError,
    OptimizationError,
)

logger = logging.getLogger(__name__)

_VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR"})


def _configure_logging(level: str) -> None:
    """Configure the root logger to write to stderr at the given level.

    Args:
        level: One of ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``
            (case-insensitive).

    Raises:
        DataValidationError: If the level string is not recognised.
    """
    level_upper = level.upper()
    if level_upper not in _VALID_LOG_LEVELS:
        raise DataValidationError(
            f"Invalid log level '{level}'. "
            f"Must be one of: {', '.join(sorted(_VALID_LOG_LEVELS))}"
        )
    logging.basicConfig(
        stream=sys.stderr,
        level=getattr(logging, level_upper),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


@click.command()
@click.option(
    "--team",
    "team_path",
    required=True,
    type=click.Path(),
    help="Path to YAML team roster file.",
)
@click.option(
    "--history",
    "history_path",
    default=None,
    type=click.Path(),
    help="Path to JSON history store file.",
)
@click.option(
    "--update-history",
    "update_history",
    is_flag=True,
    default=False,
    help="Persist new pairings to history store after run.",
)
@click.option(
    "--prune-history",
    "prune_history",
    is_flag=True,
    default=False,
    help="Remove stale history entries on write (requires --update-history).",
)
@click.option(
    "--history-weight",
    "history_weight",
    default=1.0,
    type=float,
    help="Weight applied to history repetition penalty.",
)
@click.option(
    "--tz-weight",
    "tz_weight",
    default=1.0,
    type=float,
    help="Weight applied to timezone incompatibility penalty.",
)
@click.option(
    "--solver-profile",
    "solver_profile",
    default="adaptive",
    type=str,
    help="Solver profile: fast, balanced, optimal, adaptive.",
)
@click.option(
    "--log-level",
    "log_level",
    default="INFO",
    type=str,
    help="Log verbosity: DEBUG, INFO, WARNING, ERROR.",
)
def main(
    team_path: str,
    history_path: str | None,
    update_history: bool,
    prune_history: bool,
    history_weight: float,
    tz_weight: float,
    solver_profile: str,
    log_level: str,
) -> None:
    """Generate optimised buddy pairings for a team."""
    try:
        _configure_logging(log_level)
    except DataValidationError as exc:
        _emit_failure(exc.message)
        sys.exit(1)

    try:
        _run(
            team_path=Path(team_path),
            history_path=Path(history_path) if history_path else None,
            update_history=update_history,
            prune_history=prune_history,
            history_weight=history_weight,
            tz_weight=tz_weight,
            solver_profile=solver_profile,
        )
    except OptimizationError as exc:
        _emit_failure(exc.message)
        sys.exit(2)
    except BuddySchedulerError as exc:
        _emit_failure(exc.message)
        sys.exit(1)


def _run(
    team_path: Path,
    history_path: Path | None,
    update_history: bool,
    prune_history: bool,
    history_weight: float,
    tz_weight: float,
    solver_profile: str,
) -> None:
    """Core run logic; raises BuddySchedulerError subclasses on failure."""
    from buddy_scheduler.history import empty_history, load_history, save_history
    from buddy_scheduler.models import DataValidationError
    from buddy_scheduler.solver.mip import solve_pairing
    from buddy_scheduler.solver.profiles import SolverProfile
    from buddy_scheduler.validator import load_team_roster

    # Validate numeric weights
    if history_weight < 0.0:
        raise DataValidationError(
            f"--history-weight must be >= 0.0, got {history_weight}"
        )
    if tz_weight < 0.0:
        raise DataValidationError(
            f"--tz-weight must be >= 0.0, got {tz_weight}"
        )

    # Validate solver profile
    try:
        profile = SolverProfile(solver_profile.lower())
    except ValueError as exc:
        valid = ", ".join(p.value for p in SolverProfile)
        raise DataValidationError(
            f"Unknown solver profile '{solver_profile}'. Valid: {valid}"
        ) from exc

    # Warn about --prune-history without --update-history
    if prune_history and not update_history:
        logger.warning(
            "--prune-history has no effect without --update-history; ignoring"
        )

    # Load team roster
    logger.info("Loading team roster from %s", team_path)
    members = load_team_roster(team_path)

    # Load or initialise history
    effective_history_path: Path | None = history_path
    if update_history and history_path is None:
        # Auto-infer path from team file
        effective_history_path = team_path.parent / (team_path.stem + ".history.json")
        logger.info(
            "No --history provided; will use inferred path %s",
            effective_history_path,
        )

    history = None
    if effective_history_path is not None:
        if effective_history_path.exists():
            logger.info("Loading history from %s", effective_history_path)
            history = load_history(effective_history_path)
        else:
            logger.info(
                "History file %s not found; starting with empty history",
                effective_history_path,
            )
            history = empty_history()

    # Solve
    logger.info("Starting optimisation")
    result = solve_pairing(
        members=members,
        history_weight=history_weight,
        tz_weight=tz_weight,
        history=history,
        avoidance_pairs=set(),
        profile=profile,
    )

    # Persist history if requested
    if update_history and effective_history_path is not None and result.success:
        assert history is not None
        active_names = {m.name for m in members if m.active}

        if prune_history:
            logger.info("Pruning stale history entries")
            history.prune(active_names)

        for a, b in result.pairs:
            history.increment_pair(a, b)
        if result.sitting_out:
            history.increment_sit_out(result.sitting_out)

        save_history(history, effective_history_path)
        result.history_updated = True

    # Emit JSON result
    print(json.dumps(result.to_dict(), indent=2))

    if not result.success:
        sys.exit(1)


def _emit_failure(error_message: str) -> None:
    """Print a failure JSON document to stdout."""
    print(json.dumps({"success": False, "error": error_message}, indent=2))
