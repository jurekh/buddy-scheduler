# Data Model: Performance and Fairness Tests

**Branch**: `004-performance-fairness-tests`
**Phase**: 1 — Design

This feature adds no persistent data or new production models. The "data model" here
describes the shared test data structures and helper contracts used across all four
new test files.

---

## Synthetic Team

A deterministic list of `TeamMember` instances built from an integer count and a
fixed timezone rotation.

**Fields (inputs to builder)**:

| Field       | Type  | Description                                          |
|-------------|-------|------------------------------------------------------|
| `n`         | `int` | Number of active members to generate (≥ 2)           |
| `tz_count`  | `int` | How many distinct timezones to cycle through (1–6)   |

**Output**: `list[TeamMember]` where:
- `name` = `f"Member{i:03d}"` for `i` in `range(n)`
- `timezone` = `TIMEZONES[i % tz_count]` cycling through a fixed 6-element list
- `active` = `True`
- `avoid_buddies` = `[]`

**Timezone pool** (fixed, no RNG):
```
UTC, America/New_York, Europe/London, Asia/Tokyo, America/Los_Angeles, Asia/Kolkata
```

---

## Round Result

The output captured from one call to `solve_pairing` during a multi-round simulation.

| Field         | Type                   | Source on `OptimizationResult` |
|---------------|------------------------|--------------------------------|
| `pairs`       | `list[tuple[str,str]]` | `result.pairs`                 |
| `sitting_out` | `str \| None`          | `result.sitting_out`           |
| `solve_time`  | `float`                | `result.solve_time`            |

---

## Simulation State

Accumulated state across all rounds of a fairness simulation.

| Field            | Type                      | Description                            |
|------------------|---------------------------|----------------------------------------|
| `history`        | `PairingHistory`          | Mutated in place each round            |
| `round_results`  | `list[RoundResult]`       | One entry per completed round          |
| `members`        | `list[TeamMember]`        | Unchanged throughout simulation        |

---

## Fairness Metrics

Derived statistics computed from `PairingHistory` after all rounds complete.

| Metric              | Type    | Formula                                                              |
|---------------------|---------|----------------------------------------------------------------------|
| `pair_counts`       | `list[int]` | `[history.get_pair_count(a, b) for all i<j pairs]`              |
| `pairwise_stdev`    | `float` | `statistics.pstdev(pair_counts)`                                     |
| `pairwise_max_gap`  | `int`   | `max(pair_counts) - min(pair_counts)`                                |
| `sit_out_max`       | `int`   | `max(history.sit_out_counts.values(), default=0)`                    |

**Validation rules**:
- `pairwise_stdev ≤ 0.5` — required when `history_weight > 0` (FR-006, SC-002); equals the theoretical minimum for integer counts at these round/team-size combinations
- `pairwise_max_gap ≤ 1` — secondary check for 10-member 15-round test (US3 AS1); 1 is the theoretical minimum
- `sit_out_max ≤ 2` — required for 11-member 11-round simulation (FR-007)

---

## Helper Function Contracts

### `make_team(n: int, tz_count: int = 6) -> list[TeamMember]`

Builds a deterministic synthetic team. Called from tests and from `simulate_rounds`.

### `simulate_rounds(members, n_rounds, history_weight, tz_weight, profile) -> PairingHistory`

Runs `n_rounds` consecutive solves, updating the same `PairingHistory` instance
after each. Returns the final `PairingHistory`.

Signature:
```
members:        list[TeamMember]
n_rounds:       int
history_weight: float  (≥ 0.0)
tz_weight:      float  (≥ 0.0)
profile:        SolverProfile  (default: ADAPTIVE)
→ PairingHistory
```

Raises `AssertionError` if any individual round fails (`result.success is False`).
