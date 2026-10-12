"""Data models, domain exceptions, and output serialization for buddy-scheduler."""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class BuddySchedulerError(Exception):
    """Base exception for all buddy-scheduler domain errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class FileLoadError(BuddySchedulerError):
    """Raised when a required file cannot be found, read, or parsed."""


class FileSaveError(BuddySchedulerError):
    """Raised when a file cannot be written or the write cannot be made atomic."""


class DataValidationError(BuddySchedulerError):
    """Raised when loaded data fails structural or semantic validation."""


class OptimizationError(BuddySchedulerError):
    """Raised when all solver strategies are exhausted without producing a result."""


# ---------------------------------------------------------------------------
# Team model
# ---------------------------------------------------------------------------


@dataclass
class TeamMember:
    """A person on the team, as parsed from the YAML roster file."""

    name: str
    timezone: str
    active: bool = True
    avoid_buddies: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# History model
# ---------------------------------------------------------------------------


@dataclass
class PairingHistory:
    """Persistent record of all historical pairings and sit-out events.

    ``matrix[A][B]`` equals ``matrix[B][A]`` — the number of times members A and
    B have been paired.  Missing entries implicitly equal zero.
    ``sit_out_counts[A]`` counts how many times member A has sat out.
    """

    matrix: dict[str, dict[str, int]] = field(default_factory=dict)
    sit_out_counts: dict[str, int] = field(default_factory=dict)

    def get_pair_count(self, a: str, b: str) -> int:
        """Return the number of times members *a* and *b* have been paired."""
        return self.matrix.get(a, {}).get(b, 0)

    def increment_pair(self, a: str, b: str) -> None:
        """Increment the pair count for *a*–*b* in both directions."""
        self.matrix.setdefault(a, {})[b] = self.matrix.get(a, {}).get(b, 0) + 1
        self.matrix.setdefault(b, {})[a] = self.matrix.get(b, {}).get(a, 0) + 1

    def increment_sit_out(self, name: str) -> None:
        """Increment the sit-out count for *name*."""
        self.sit_out_counts[name] = self.sit_out_counts.get(name, 0) + 1

    def prune(self, active_names: set[str]) -> None:
        """Remove all entries for members not in *active_names*."""
        stale = {k for k in self.matrix if k not in active_names}
        for k in stale:
            del self.matrix[k]
        for row in self.matrix.values():
            for k in stale:
                row.pop(k, None)
        for k in stale:
            self.sit_out_counts.pop(k, None)


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


@dataclass
class OptimizationResult:
    """The output of a single buddy-pairing run, serialized to JSON on stdout."""

    success: bool
    pairs: list[tuple[str, str]]
    sitting_out: str | None
    optimization_score: float
    solve_time: float
    solver_profile: str
    solver_gap: float | None = None
    peak_memory_mb: float | None = None
    memory_delta_mb: float | None = None
    inactive_members: list[str] = field(default_factory=list)
    avoidance_conflicts: list[str] = field(default_factory=list)
    error: str | None = None
    history_updated: bool = False

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-compatible dict.

        Optional fields with a ``None`` value are omitted.  Pairs are sorted
        lexicographically within each pair and across pairs.
        """
        sorted_pairs: list[list[str]] = sorted([sorted([a, b]) for a, b in self.pairs])
        d: dict[str, object] = {
            "success": self.success,
            "pairs": sorted_pairs,
            "sitting_out": self.sitting_out,
            "optimization_score": self.optimization_score,
            "solve_time": self.solve_time,
            "solver_profile": self.solver_profile,
            "history_updated": self.history_updated,
        }
        if self.solver_gap is not None:
            d["solver_gap"] = self.solver_gap
        if self.peak_memory_mb is not None:
            d["peak_memory_mb"] = self.peak_memory_mb
        if self.memory_delta_mb is not None:
            d["memory_delta_mb"] = self.memory_delta_mb
        if self.inactive_members:
            d["inactive_members"] = self.inactive_members
        if self.avoidance_conflicts:
            d["avoidance_conflicts"] = self.avoidance_conflicts
        if self.error is not None:
            d["error"] = self.error
        return d
