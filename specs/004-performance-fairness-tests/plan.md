# Implementation Plan: Performance and Fairness Tests

**Branch**: `004-performance-fairness-tests` | **Date**: 2026-03-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-performance-fairness-tests/spec.md`

## Summary

Add a `tests/performance/` module containing four test files and a shared helper
module that cover: (1) wall-clock timing thresholds for small/medium/large and
odd/even team sizes; (2) memory metric correctness and bounding; (3) multi-round
fairness simulation with statistical distribution assertions; (4) adaptive solver
profile resolution and time-monotonicity regression. All tests are marked
`@pytest.mark.slow` and excluded from the default `pytest` run. No production code
is modified.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: PuLP ≥ 2.7 (CBC solver), psutil ≥ 5.9, pytest ≥ 7.0 — all already in `pyproject.toml`; `statistics` (stdlib)
**Storage**: N/A — tests operate entirely in memory; no file I/O
**Testing**: pytest + pytest-cov; `@pytest.mark.slow` excludes tests from default run
**Target Platform**: Linux CI (same as existing tests)
**Project Type**: CLI tool — test additions only
**Performance Goals**: Each timing test must pass within documented per-size thresholds (see research.md Decision 5)
**Constraints**: Peak memory < 50 MB for 50-member full-history run (measured ~23.4 MB); fairness std-dev ≤ 0.5 and max-gap ≤ 1 after ≥ 10 rounds (theoretical minimum for integer distributions)
**Scale/Scope**: Teams up to 100 active members; fairness simulations up to 15 rounds

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment | Status |
|-----------|------------|--------|
| I. Type Safety | All new test helpers and fixtures use explicit type annotations; `mypy --strict` must pass on `tests/performance/` | ✅ Required |
| II. Data Integrity | No persistent state written in tests; atomicity and locking requirements do not apply | ✅ N/A |
| III. Comprehensive Testing | **Key gate**: Long-running tests MUST carry `@pytest.mark.slow` so they are excluded from the default run. Coverage must not drop below 80%. Tests must exercise error paths (e.g., infeasibility with avoidance constraints). | ✅ Satisfied by design (see Decision 1 in research.md) |
| IV. Transparent Operations | N/A for test code | ✅ N/A |
| V. Explicit Failure Reporting | N/A for test code | ✅ N/A |
| Code Quality | ruff and mypy must pass; public helpers must have docstrings; no wildcard imports | ✅ Required |

**No violations. No complexity tracking needed.**

## Project Structure

### Documentation (this feature)

```text
specs/004-performance-fairness-tests/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks — not yet created)
```

### Source Code (repository root)

```text
tests/
├── contract/            # unchanged
├── integration/         # unchanged
├── unit/                # unchanged
└── performance/         # NEW
    ├── __init__.py
    ├── conftest.py      # make_team(), simulate_rounds() helpers
    ├── test_timing.py   # FR-001, FR-002, FR-011
    ├── test_memory.py   # FR-003, FR-004, FR-005
    ├── test_fairness.py # FR-006, FR-007, FR-008, FR-012
    └── test_profiles.py # FR-009; US4 monotonicity
```

**Structure Decision**: Single project layout (existing layout). All new files go
under `tests/performance/`. No changes to `src/` or `pyproject.toml`.

## Phase 0: Research

All unknowns resolved. See [research.md](research.md) for full decision log.

Key findings:
- `@pytest.mark.slow` is already configured and excluded from the default run — no `pyproject.toml` change needed.
- No `conftest.py` exists anywhere in the test tree; `tests/performance/conftest.py` will be the first.
- `solve_pairing()` signature confirmed; `OptimizationResult` fields `peak_memory_mb`, `memory_delta_mb`, `solve_time`, `solver_profile` are all populated by the existing solver.
- Adaptive thresholds: N ≤ 15 → `"optimal"`, 16–60 → `"balanced"`, > 60 → `"fast"`. Boundary values (15, 16, 60, 61) must each be tested.
- `PairingHistory.increment_pair()` and `increment_sit_out()` are the correct update methods; no mocking needed.
- `statistics.pstdev()` (stdlib) chosen for fairness std-dev computation.
- `time.monotonic()` for wall-clock measurement.

## Phase 1: Design

See [data-model.md](data-model.md) for entity definitions and helper contracts.
See [quickstart.md](quickstart.md) for how to run tests.

No `contracts/` directory is needed — this feature adds no new public interfaces.

### File-by-file design notes

#### `tests/performance/conftest.py`

Provides two module-scope helpers (plain functions, not pytest fixtures, since they
take parameters and are called directly):

- `make_team(n: int, tz_count: int = 6) -> list[TeamMember]`
  Builds a deterministic team. See data-model.md.

- `simulate_rounds(members, n_rounds, history_weight, tz_weight, profile) -> PairingHistory`
  Runs N consecutive solves, updating history in place. Asserts each round succeeds.
  Returns the final `PairingHistory`.

Both functions carry full docstrings and type annotations to satisfy the constitution's
Code Quality Standards.

---

#### `tests/performance/test_timing.py`

All tests marked `@pytest.mark.slow`.

| Test | Team size | Profile | Threshold | Odd/Even |
|------|-----------|---------|-----------|----------|
| `test_small_even_timing` | 10 | adaptive → optimal | 30 s | even |
| `test_small_odd_timing` | 11 | adaptive → optimal | 30 s | odd |
| `test_medium_even_timing` | 30 | adaptive → balanced | 10 s | even |
| `test_medium_odd_timing` | 35 | adaptive → balanced | 15 s | odd |
| `test_large_even_timing` | 50 | adaptive → balanced | 30 s | even |
| `test_large_odd_timing` | 25 | adaptive → balanced | 10 s | odd |
| `test_very_large_even_timing` | 100 | adaptive → fast | 5 s | even |
| `test_dense_history_timing` | 20 | adaptive → balanced | 10 s | even, full history |

Each test:
1. Builds team with `make_team(n)`.
2. Records `time.monotonic()` before/after `solve_pairing(...)`.
3. Asserts `result.success`.
4. Asserts `elapsed < THRESHOLD`.

Dense history test also populates `PairingHistory` with all-pairs counts before timing.

---

#### `tests/performance/test_memory.py`

All tests marked `@pytest.mark.slow`.

| Test | Assertion |
|------|-----------|
| `test_memory_fields_populated` | `peak_memory_mb > 0` and `memory_delta_mb >= 0` after any successful solve |
| `test_memory_fields_populated_min_team` | Same, for 2-member team (minimum valid) |
| `test_memory_scales_with_team_size` | `large.memory_delta_mb >= small.memory_delta_mb` for N=6 vs N=50 |
| `test_peak_memory_upper_bound_50_members` | `peak_memory_mb < 50` for N=50 with full history matrix (measured ~23.4 MB) |
| `test_memory_fields_on_infeasible` | Memory fields are present even when avoidance causes infeasibility |

The infeasibility test (last row) uses a 4-member team where one member avoids all
others, confirming memory metrics are populated regardless of success/failure.

---

#### `tests/performance/test_fairness.py`

All tests marked `@pytest.mark.slow`.

| Test | Rounds | Team | history_weight | Assertion |
|------|--------|------|----------------|-----------|
| `test_pairwise_stdev_10_members` | 15 | 10 even | 1.0 | `pstdev ≤ 0.5` and `max_gap ≤ 1` (theoretical minimum) |
| `test_pairwise_stdev_20_members` | 10 | 20 even | 1.0 | `pstdev ≤ 0.5` (theoretical minimum) |
| `test_sitout_rotation_11_members` | 11 | 11 odd | 1.0 | `max(sit_out_counts) ≤ 2` |
| `test_cross_tz_pairings_occur` | 10 | 12, 2 TZs | 1.0 | At least one cross-timezone pair appears |
| `test_zero_history_weight_no_fairness_required` | 5 | 10 even | 0.0 | Passes unconditionally (documents precondition) |

Each test calls `simulate_rounds(...)` then computes fairness metrics over the
returned `PairingHistory`.

`test_cross_tz_pairings_occur`: Uses `tz_count=2` so half the team is in timezone A
and half in timezone B. Asserts that after 10 rounds with `history_weight=1.0`, at
least one pair from different timezone groups appears in the accumulated history.

`test_zero_history_weight_no_fairness_required`: Runs 5 rounds, makes no assertion
on distribution. The test exists to document that fairness is a consequence of
history weight, not a hard constraint of the solver.

---

#### `tests/performance/test_profiles.py`

All tests marked `@pytest.mark.slow`.

**Class `TestAdaptiveProfileResolution`** — verifies profile name on result:

| Test | N | Expected `solver_profile` |
|------|---|--------------------------|
| `test_n15_resolves_optimal` | 15 | `"optimal"` |
| `test_n16_resolves_balanced` | 16 | `"balanced"` |
| `test_n60_resolves_balanced` | 60 | `"balanced"` |
| `test_n61_resolves_fast` | 61 | `"fast"` |
| `test_n100_resolves_fast` | 100 | `"fast"` |

**Class `TestSolveTimeMonotonicity`**:

| Test | Team sizes | Assertion |
|------|------------|-----------|
| `test_monotonic_10_20_30` | [10, 20, 30] | `solve_time(30) >= solve_time(10)` |

Note: monotonicity is soft (≥ not >), allowing for variance at small sizes. The
test uses the result's `solve_time` field (recorded by the solver) rather than
external `time.monotonic()` to avoid process-startup overhead skewing small solves.

**Class `TestExplicitProfiles`**:

| Test | N | Profiles | Assertion |
|------|---|----------|-----------|
| `test_all_explicit_profiles_succeed` | 20 | fast, balanced, optimal | `result.success` for all three |

This confirms no profile raises an exception on a medium-sized team.
