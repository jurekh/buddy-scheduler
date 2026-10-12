# Data Model: buddy-scheduler

**Branch**: `001-buddy-scheduler` | **Date**: 2026-02-24

## Entities

### TeamMember

Represents a person on the team. Loaded from the YAML team roster file.

```python
@dataclass
class TeamMember:
    name: str                       # Unique identifier within the roster
    timezone: str                   # Free-form string (e.g. "UTC+1", "America/New_York")
    active: bool = True             # False = excluded from pairing
    avoid_buddies: list[str] = []   # Names of members who must never be paired with this person
```

**Validation rules**:
- `name` MUST be non-empty and unique within the roster; duplicates are a
  `DataValidationError`.
- `timezone` MUST be non-empty.
- `avoid_buddies` entries that name non-existent members are silently ignored (no
  error; they can never be resolved and therefore never trigger a constraint).
- Avoidance is enforced symmetrically: if A lists B, the pair A–B is forbidden
  regardless of whether B lists A.

---

### SolverProfile

Enum controlling MIP solver settings.

```python
class SolverProfile(Enum):
    FAST     = "fast"      # Wide gap tolerance (20%), minimal branching, short time limit
    BALANCED = "balanced"  # Moderate gap tolerance (1%), default branching
    OPTIMAL  = "optimal"   # Tight gap tolerance (0.1%), aggressive branching
    ADAPTIVE = "adaptive"  # Automatically selects OPTIMAL / BALANCED / FAST by team size
```

**ADAPTIVE selection thresholds**:
- ≤ 15 active members → OPTIMAL
- 16–60 active members → BALANCED
- > 60 active members → FAST

---

### PairingHistory

Persistent state tracking all historical pairings and sit-out events. Stored in a
JSON file managed exclusively by the tool.

```python
@dataclass
class PairingHistory:
    matrix: dict[str, dict[str, int]]
    # Symmetric match-count matrix.
    # matrix[A][B] == matrix[B][A] == number of times A and B have been paired.
    # Diagonal entries (matrix[A][A]) are unused.
    # Missing entries implicitly equal 0 (new member or never paired).

    sit_out_counts: dict[str, int]
    # Per-member sit-out count across all historical runs.
    # Used to drive fair sit-out rotation (prefer member with lowest count).
```

**Validation rules** (applied on load):
- Matrix MUST be symmetric: for every stored pair (A, B), `matrix[A][B]` MUST equal
  `matrix[B][A]`. Asymmetric matrices raise `DataValidationError`.
- All count values MUST be non-negative integers.
- Entries for members absent from the current roster are silently ignored during
  pairing; they are pruned only when `--prune-history` is requested alongside
  `--update-history`.

**Write contract**:
- Written atomically: to a temporary file in the same directory → `fsync` →
  `os.replace` (atomic rename).
- The previous version is backed up to `<path>.backup` before the rename.
- Concurrent write access is serialised with `fcntl.lockf(LOCK_EX)`.

---

### OptimizationResult

The output of a single run, serialised to JSON on stdout.

```python
@dataclass
class OptimizationResult:
    pairs: list[tuple[str, str]]       # Sorted pairs (alphabetical within pair, pairs sorted by first member)
    sitting_out: str | None            # Name of sit-out member; None for even teams
    success: bool                      # True if a valid solution was found (MIP or fallback)
    optimization_score: float          # Total weighted penalty; 0.0 on failure
    solve_time: float                  # Wall-clock seconds for the full run
    solver_profile: str                # Resolved profile name, or "<profile>_fallback_<strategy>"
    solver_gap: float | None = None    # Achieved MIP gap; present only for MIP solutions
    peak_memory_mb: float | None = None
    memory_delta_mb: float | None = None
    inactive_members: list[str] = []
    avoidance_conflicts: list[str] = []  # Non-empty only when run failed due to infeasible constraints
    error: str | None = None             # Non-None only on unexpected exception
    history_updated: bool = False
```

**solver_profile encoding**:
- MIP solution: profile name as resolved (e.g. `"optimal"`, `"fast"`, `"balanced"`).
  When ADAPTIVE is used, the resolved profile name is emitted (not `"adaptive"`).
- Fallback solution: `"<resolved_profile>_fallback_<strategy>"`,
  e.g. `"fast_fallback_greedy_min_penalty"`.

---

## Exception Hierarchy

```python
BuddySchedulerError(Exception)          # Base; all domain errors
├── FileLoadError(BuddySchedulerError)   # File not found, unreadable, empty, malformed
├── FileSaveError(BuddySchedulerError)   # Write failure, lock timeout
├── DataValidationError(BuddySchedulerError)  # Invalid roster or history content
└── OptimizationError(BuddySchedulerError)    # All fallbacks exhausted; no solution found
```

---

## MIP Formulation (summary)

**Decision variables**:
- `x_{ij} ∈ {0, 1}` for each eligible pair (i, j) where i < j, both active, and
  (i, j) not in the avoidance set.
- `s_i ∈ {0, 1}` for each active member i, indicating whether i sits out (used only
  when the active member count is odd; exactly one `s_i = 1`).

**Hard constraints**:
- Each active member appears in exactly one pair OR sits out.
- For even teams: `∑_j x_{ij} = 1` for all active i.
- For odd teams: `∑_j x_{ij} + s_i = 1` for all active i, `∑_i s_i = 1`.
- Avoidance: `x_{ij} = 0` for all (i, j) in the avoidance set.

**Objective** (minimise):
```
∑_{(i,j)} x_{ij} × (history_weight × history_penalty(i, j)
                   + timezone_weight × timezone_penalty(i, j))
+ ∑_i s_i × sit_out_penalty(i)
```

**Penalty functions**:
- `history_penalty(i, j)` = `matrix[i][j]` (raw count; higher = more repeated).
- `timezone_penalty(i, j)` = `1 - difflib.SequenceMatcher(None, tz_i, tz_j).ratio()`
  (0 = identical timezone strings, 1 = completely dissimilar).
- `sit_out_penalty(i)` = `sit_out_counts[i]` (prefer members who have sat out
  least).
