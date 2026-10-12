# Tasks: Performance and Fairness Tests

**Input**: Design documents from `/specs/004-performance-fairness-tests/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation
and testing of each story. All tests carry `@pytest.mark.slow` and are excluded from
the default `pytest` run per research.md Decision 1.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Exact file paths included in all descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the `tests/performance/` package so Python treats it as a module
and pytest discovers tests within it.

- [x] T001 Create `tests/performance/__init__.py` as an empty package marker file

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared helpers used by every test in every story. Must be complete before
any story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 Implement `make_team(n: int, tz_count: int = 6) -> list[TeamMember]` in `tests/performance/conftest.py` — builds deterministic teams using `f"Member{i:03d}"` names and `TIMEZONES[i % tz_count]` cycling through `["UTC", "America/New_York", "Europe/London", "Asia/Tokyo", "America/Los_Angeles", "Asia/Kolkata"]`; all members active with no avoid_buddies; include module-level `TIMEZONES` constant and full docstring
- [x] T003 Implement `simulate_rounds(members, n_rounds, history_weight, tz_weight, profile) -> PairingHistory` in `tests/performance/conftest.py` — runs N consecutive `solve_pairing` calls mutating the same `PairingHistory` in place; calls `history.increment_pair(a, b)` for each pair and `history.increment_sit_out(name)` when sitting_out is set; asserts each round succeeds; returns final history; full type annotations and docstring required

**Checkpoint**: `make_team` and `simulate_rounds` importable from `tests/performance/conftest.py`

---

## Phase 3: User Story 1 — Timing Tests (Priority: P1) 🎯 MVP

**Goal**: Assert that the solver completes within documented per-size thresholds for
all team-size bands (small/medium/large, even and odd).

**Independent Test**: `cd src && pytest -m slow tests/performance/test_timing.py -v`

- [x] T004 [US1] Create `tests/performance/test_timing.py` with module-level timing constants (`SMALL_THRESHOLD_S = 30`, `MEDIUM_THRESHOLD_S = 10`, `MEDIUM_ODD_THRESHOLD_S = 15`, `LARGE_THRESHOLD_S = 30`, `VERY_LARGE_THRESHOLD_S = 5`, `DENSE_HISTORY_THRESHOLD_S = 10`) and implement `test_small_even_timing`: N=10 team with `SolverProfile.ADAPTIVE`, assert `elapsed < SMALL_THRESHOLD_S` and `result.success`; mark all tests `@pytest.mark.slow`; use `time.monotonic()` for measurement
- [x] T005 [US1] Add `test_small_odd_timing` to `tests/performance/test_timing.py`: N=11 team with adaptive profile, assert `elapsed < SMALL_THRESHOLD_S`, `result.success`, and `result.sitting_out is not None`
- [x] T006 [US1] Add medium-team timing tests to `tests/performance/test_timing.py`: `test_medium_even_timing` (N=30, `< MEDIUM_THRESHOLD_S`) and `test_medium_odd_timing` (N=35, `< MEDIUM_ODD_THRESHOLD_S`); both assert `result.success` and correct `len(result.pairs)` for even/odd
- [x] T007 [US1] Add `test_large_odd_timing` (N=25, `< MEDIUM_THRESHOLD_S`) and `test_large_even_timing` (N=50, `< LARGE_THRESHOLD_S`) to `tests/performance/test_timing.py`; assert `result.success` and pair counts match team size
- [x] T008 [US1] Add `test_very_large_even_timing` (N=100, `< VERY_LARGE_THRESHOLD_S`) to `tests/performance/test_timing.py`; this matches the existing `test_performance_100_members` threshold already proven in `tests/unit/test_mip.py`
- [x] T009 [US1] Add `test_dense_history_timing` to `tests/performance/test_timing.py`: N=20 team; pre-populate `PairingHistory` with all-pairs counts using nested loops `history.increment_pair(f"Member{i:03d}", f"Member{j:03d}")` for `i < j`; run solver; assert `elapsed < DENSE_HISTORY_THRESHOLD_S` and `result.success`

**Checkpoint**: `pytest -m slow tests/performance/test_timing.py` passes with 8 tests

---

## Phase 4: User Story 2 — Memory Tests (Priority: P2)

**Goal**: Verify that `peak_memory_mb` and `memory_delta_mb` are populated, non-negative,
scale with team size, and stay below the 200 MB ceiling for a 50-member full-history run.

**Independent Test**: `cd src && pytest -m slow tests/performance/test_memory.py -v`

- [x] T010 [P] [US2] Create `tests/performance/test_memory.py` with `test_memory_fields_populated`: build a 10-member team using `make_team(10)`, call `solve_pairing`, assert `result.peak_memory_mb is not None`, `result.peak_memory_mb > 0`, `result.memory_delta_mb is not None`, `result.memory_delta_mb >= 0`; mark `@pytest.mark.slow`
- [x] T011 [US2] Add `test_memory_fields_populated_min_team` to `tests/performance/test_memory.py`: 2-member team (minimum valid), same field assertions; confirms memory tracking works at minimum team size
- [x] T012 [US2] Add `test_memory_scales_with_team_size` to `tests/performance/test_memory.py`: run two solves — `small` with `make_team(6)` and `large` with `make_team(50)` — both with no history; assert `large.memory_delta_mb >= small.memory_delta_mb` and both `memory_delta_mb` values are non-None
- [x] T013 [US2] Add `test_peak_memory_upper_bound_50_members` to `tests/performance/test_memory.py`: build `make_team(50)`, pre-populate `PairingHistory` with all N×(N-1)/2 pair counts (deterministic via nested loop), run solver, assert `result.peak_memory_mb is not None` and `result.peak_memory_mb < 200.0`
- [x] T014 [US2] Add `test_memory_fields_on_infeasible` to `tests/performance/test_memory.py`: create 4-member team where `Member000` has `avoid_buddies=["Member001", "Member002", "Member003"]`; call `solve_pairing`; assert `result.success is False`; assert `result.peak_memory_mb is not None` and `result.memory_delta_mb is not None` (metrics present regardless of success/failure)

**Checkpoint**: `pytest -m slow tests/performance/test_memory.py` passes with 5 tests

---

## Phase 5: User Story 3 — Fairness Tests (Priority: P2)

**Goal**: Verify that the history-weighted solver distributes pairings equitably across
multiple consecutive rounds, measured by pairwise std-dev, max-gap, and sit-out spread.

**Independent Test**: `cd src && pytest -m slow tests/performance/test_fairness.py -v`

- [x] T015 [P] [US3] Create `tests/performance/test_fairness.py` with `_pairwise_counts(history, member_names)` private helper that returns a list of `history.get_pair_count(a, b)` for all unique pairs `i < j`; implement `test_pairwise_stdev_10_members`: call `simulate_rounds(make_team(10), 15, 1.0, 0.0)`; compute counts; assert `statistics.pstdev(counts) <= 1.5` and `max(counts) - min(counts) <= 2`; mark `@pytest.mark.slow`
- [x] T016 [US3] Add `test_pairwise_stdev_20_members` to `tests/performance/test_fairness.py`: `simulate_rounds(make_team(20), 10, 1.0, 0.0)`; compute pairwise counts; assert `statistics.pstdev(counts) <= 1.5`
- [x] T017 [US3] Add `test_sitout_rotation_11_members` to `tests/performance/test_fairness.py`: `simulate_rounds(make_team(11), 11, 1.0, 0.0)`; assert `len(history.sit_out_counts) > 0`; assert `max(history.sit_out_counts.values()) <= 2`
- [x] T018 [US3] Add `test_cross_tz_pairings_occur` to `tests/performance/test_fairness.py`: build `make_team(12, tz_count=2)` so first 6 members are `TIMEZONES[0]` and last 6 are `TIMEZONES[1]`; `simulate_rounds(members, 10, 1.0, 0.0)`; assert at least one pair in `history.matrix` has members from different timezone groups (i.e., one index < 6 paired with one index >= 6 at count > 0)
- [x] T019 [US3] Add `test_zero_history_weight_no_fairness_required` to `tests/performance/test_fairness.py`: `simulate_rounds(make_team(10), 5, 0.0, 0.0)`; assert every round succeeded (checked inside `simulate_rounds`); make **no assertion** on distribution; add a comment `# history_weight=0 → fairness not guaranteed; this test documents the precondition`

**Checkpoint**: `pytest -m slow tests/performance/test_fairness.py` passes with 5 tests

---

## Phase 6: User Story 4 — Profile Resolution and Monotonicity Tests (Priority: P3)

**Goal**: Regression-test the adaptive profile threshold logic at every boundary value and
confirm solve time grows with team size.

**Independent Test**: `cd src && pytest -m slow tests/performance/test_profiles.py -v`

- [x] T020 [P] [US4] Create `tests/performance/test_profiles.py` with class `TestAdaptiveProfileResolution`; implement five tests — `test_n15_resolves_optimal`, `test_n16_resolves_balanced`, `test_n60_resolves_balanced`, `test_n61_resolves_fast`, `test_n100_resolves_fast` — each calls `solve_pairing(make_team(N), 0.0, 0.0, None, set(), SolverProfile.ADAPTIVE)` and asserts `result.solver_profile == "optimal"|"balanced"|"fast"` as appropriate; mark all `@pytest.mark.slow`
- [x] T021 [US4] Add class `TestSolveTimeMonotonicity` to `tests/performance/test_profiles.py` with `test_monotonic_10_20_30`: run solves for N=10, N=20, N=30 with `SolverProfile.ADAPTIVE` and no history; collect `result.solve_time` for each; assert `times[2] >= times[0]` (30-member solve_time ≥ 10-member solve_time); use `result.solve_time` (solver-reported) not `time.monotonic()` to avoid startup noise
- [x] T022 [US4] Add class `TestExplicitProfiles` to `tests/performance/test_profiles.py` with `test_all_explicit_profiles_succeed`: for each of `SolverProfile.FAST`, `SolverProfile.BALANCED`, `SolverProfile.OPTIMAL` call `solve_pairing(make_team(20), 0.0, 0.0, None, set(), profile)` and assert `result.success is True` and `result.solver_profile == profile.value`

**Checkpoint**: `pytest -m slow tests/performance/test_profiles.py` passes with 9 tests

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Type correctness, linting, and final validation of the full suite.

- [x] T023 Run `cd src && ruff check ../tests/performance/` and fix all lint violations (unused imports, line length, etc.)
- [x] T024 Run `cd src && mypy --strict ../tests/performance/` and fix all type errors; ensure `conftest.py`, `test_timing.py`, `test_memory.py`, `test_fairness.py`, `test_profiles.py` all pass strict mode
- [x] T025 Run `cd src && pytest -m slow -v` to execute the full performance test suite and confirm all 27 tests pass
- [x] T026 Run `cd src && pytest --cov=buddy_scheduler --cov-report=term-missing` (default run, no slow) and confirm coverage remains ≥ 80% and no previously passing tests are broken

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on T001 — blocks all user stories
- **User Stories (Phases 3–6)**: All depend on T002 + T003 (conftest.py complete)
  - Phases 3, 4, 5, 6 can proceed in parallel once Phase 2 is done (all create separate files)
- **Polish (Phase 7)**: Depends on all story phases complete

### User Story Dependencies

- **US1 (P1, test_timing.py)**: Can start after Phase 2 — no dependency on other stories
- **US2 (P2, test_memory.py)**: Can start after Phase 2 — independent of US1
- **US3 (P2, test_fairness.py)**: Can start after Phase 2 — independent of US1/US2
- **US4 (P3, test_profiles.py)**: Can start after Phase 2 — independent of all above

### Within Each User Story

- Tasks within a story are sequential (they all edit the same file)
- First task in each story creates the file; subsequent tasks add to it
- Each task adds one or two test functions and can be verified incrementally with `pytest -m slow tests/performance/test_<name>.py::<function_name>`

### Parallel Opportunities

- T010 [US2], T015 [US3], T020 [US4] can all start simultaneously after T002+T003 complete
- T001 and T002 are strictly sequential (T002 requires the package to exist from T001)
- T023 and T024 can run in parallel (ruff and mypy check different things, same files)

---

## Parallel Example: Post-Phase-2 Execution

```bash
# Once T002+T003 are done, launch all stories simultaneously:
Task A: T004–T009 (test_timing.py — US1)
Task B: T010–T014 (test_memory.py — US2)
Task C: T015–T019 (test_fairness.py — US3)
Task D: T020–T022 (test_profiles.py — US4)

# Verify each independently as they complete:
pytest -m slow tests/performance/test_timing.py    # US1 done
pytest -m slow tests/performance/test_memory.py    # US2 done
pytest -m slow tests/performance/test_fairness.py  # US3 done
pytest -m slow tests/performance/test_profiles.py  # US4 done
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (T001)
2. Complete Phase 2 (T002–T003)
3. Complete Phase 3 (T004–T009)
4. **STOP and VALIDATE**: `pytest -m slow tests/performance/test_timing.py` — 8 timing tests pass
5. Timing regressions are now caught for all team-size bands

### Incremental Delivery

1. Setup + Foundational → conftest helpers ready
2. US1 timing tests → CI catches solver speed regressions
3. US2 memory tests → CI catches memory growth regressions
4. US3 fairness tests → CI catches fairness distribution regressions
5. US4 profile tests → CI catches adaptive threshold regressions
6. Polish → ruff + mypy clean, coverage gate holds

---

## Notes

- `@pytest.mark.slow` on every test in `tests/performance/` — excluded by default `pytest` run via `addopts = "-m 'not slow'"` in `pyproject.toml`; no `pyproject.toml` change required
- `simulate_rounds` asserts each round succeeds internally — a failing solve inside a fairness test will raise `AssertionError` with a clear message indicating which round failed
- The dense-history pre-population in T009 and T013 uses deterministic nested loops, not `PairingHistory.increment_pair` in a random order, ensuring reproducibility
- `statistics.pstdev` (stdlib, population std-dev) is correct here — we enumerate the entire pair space, not a sample
- `result.solve_time` (solver-reported) is used for monotonicity in T021; external `time.monotonic()` is used for threshold tests (T004–T009) to capture total wall-clock latency including Python overhead
