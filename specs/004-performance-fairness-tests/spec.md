# Feature Specification: Performance and Fairness Tests

**Feature Branch**: `004-performance-fairness-tests`
**Created**: 2026-03-02
**Status**: Draft
**Input**: Add a test suite covering two distinct areas:

1. **Performance tests** — measure wall-clock solve time and process memory (peak RSS and delta) for the scheduling algorithm across team sizes: small (≤ 15), medium (16–60), and large (> 60) active members, including odd-sized teams. Each test asserts that solve time stays below a documented per-size threshold and that memory metrics are populated and within expected bounds.

2. **Fairness analysis tests** — simulate multiple consecutive scheduling rounds (≥ 10), updating history after each round, and assert that the algorithm distributes buddy pairings equitably over time. Metrics: standard deviation of per-pair meeting counts (≤ 0.5, the theoretical minimum for integer-valued distributions at these round counts), max-gap ≤ 1, and sit-out rotation for odd-sized teams (no member sits out more than twice in 11 rounds for an 11-member team).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Algorithm speed meets defined thresholds for all team sizes (Priority: P1)

A developer running the test suite wants assurance that the scheduling algorithm
solves within acceptable wall-clock time at each supported team scale. The tests
simulate teams of various sizes (small ~10, medium ~30–40, large ~60–100) and assert
that solve time stays below per-size thresholds. Odd-numbered teams (one member sits
out) are tested separately because the search space differs slightly.

**Why this priority**: Speed regressions are the most operationally disruptive — users
waiting on the CLI command notice immediately. A failing timing test is the first
signal that a solver change broke the performance contract.

**Independent Test**: Can be run on its own by executing the performance test file;
delivers clear pass/fail evidence of speed compliance at every team size.

**Acceptance Scenarios**:

1. **Given** a team of 30 active members with no prior history, **When** the scheduler
   runs with the adaptive profile, **Then** a valid pairing is produced within 10 seconds.
2. **Given** a team of 50 active members with no prior history, **When** the scheduler
   runs with the adaptive profile, **Then** a valid pairing is produced within 30 seconds.
3. **Given** a team of 100 active members with no prior history, **When** the scheduler
   runs with the adaptive profile, **Then** a valid pairing is produced within 5 seconds
   (fast profile is selected automatically).
4. **Given** an odd-sized team (e.g. 25 or 35 members), **When** the scheduler runs,
   **Then** exactly one member sits out and the result is produced within the same
   time limit as a comparable even-sized team.
5. **Given** a team with a dense pairing history (every pair has been scheduled
   multiple times before), **When** the scheduler runs, **Then** solve time stays
   within the same thresholds as an equivalent no-history run.

---

### User Story 2 - Memory usage stays bounded and scales predictably (Priority: P2)

A developer wants confidence that the scheduler does not consume unbounded memory
as team size grows, and that the reported peak-memory and memory-delta metrics are
accurate. Tests measure actual process memory before and after a solve, compare
small vs. large teams, and verify that the metrics exposed on the result object are
populated and self-consistent.

**Why this priority**: Unbounded memory growth causes OOM crashes on constrained CI
runners or large deployments, but memory issues are less immediately visible than
speed issues to end users.

**Independent Test**: Can be run in isolation; confirms memory fields are populated
and that a larger team uses no less memory than a smaller one under identical conditions.

**Acceptance Scenarios**:

1. **Given** any successful solve, **When** the result is inspected, **Then**
   `peak_memory_mb` is a positive number and `memory_delta_mb` is non-negative.
2. **Given** a small team (6 members) and a large team (50 members) run back-to-back
   under identical conditions, **When** both complete, **Then** the large team's
   `memory_delta_mb` is greater than or equal to the small team's.
3. **Given** a team of 50 members with a fully-populated prior history matrix,
   **When** the scheduler runs, **Then** the incremental memory allocated by the
   solve (delta, not absolute RSS) stays below 5 MB.
4. **Given** the minimum valid team size (2 active members), **When** the scheduler
   runs, **Then** both memory metrics are non-negative and the solve completes
   without error.

---

### User Story 3 - Fairness analysis: pairings distribute evenly across rounds (Priority: P2)

A developer wants evidence that the algorithm distributes buddy pairings fairly over
multiple consecutive scheduling rounds. After simulating N rounds (updating history
after each), the tests assert that:
- No pair of individuals is scheduled together significantly more often than others.
- Sit-out duty rotates across team members rather than concentrating on a subset.
- The standard deviation of per-pair counts and per-person sit-out counts stays
  within a defined tolerance.

**Why this priority**: Fairness violations are the primary user-visible quality issue
(users complain "I always get paired with the same person") but do not surface
until multiple rounds have been run, making them easy to miss without explicit multi-round tests.

**Independent Test**: Can be run alone; simulates a configurable number of rounds on
a synthetic team and reports min/max/std-dev of pairing and sit-out distributions.

**Acceptance Scenarios**:

1. **Given** a team of 10 members with no prior history and history_weight > 0,
   **When** 15 rounds are simulated with history updated after each round, **Then**
   the maximum difference between any two pairs' total pairing counts is ≤ 1.
2. **Given** a team of 20 members with no prior history and history_weight > 0,
   **When** 10 rounds are simulated, **Then** the standard deviation of all
   pairwise meeting counts does not exceed 0.5.
3. **Given** an odd-sized team of 11 members, **When** 11 rounds are simulated,
   **Then** each member sits out at most twice (ideally once each in a fair rotation).
4. **Given** a team where some members share the same timezone and history_weight > 0,
   **When** multiple rounds are simulated, **Then** timezone-group pairs are not
   repeated exclusively; cross-group pairings also occur over time.
5. **Given** history_weight = 0.0, **When** multiple rounds are run, **Then** the
   distribution of pair counts is not required to be fair (confirming weight drives
   the behaviour).

---

### User Story 4 - Solver profile selection and time-scaling validation (Priority: P3)

A developer wants regression tests confirming that solve time increases monotonically
with team size (within statistical noise), and that each named solver profile
(fast, balanced, optimal, adaptive) produces a valid result with the expected
trade-off properties (faster profiles finish in less time; optimal is most thorough
for small teams).

**Why this priority**: These tests document solver behaviour and catch regressions in
the adaptive profile-selection logic (e.g., thresholds changing inadvertently).

**Independent Test**: Can be run alone; sweeps several team sizes and records solve
times and reported profile names to verify monotonicity and profile resolution.

**Acceptance Scenarios**:

1. **Given** teams of size 10, 20, and 30 run with identical settings, **When** solve
   times are compared, **Then** solve_time(30) ≥ solve_time(10).
2. **Given** a team of 10 active members, **When** the adaptive profile is used,
   **Then** the resolved profile name reported on the result is "optimal".
3. **Given** a team of 20 active members, **When** the adaptive profile is used,
   **Then** the resolved profile name is "balanced".
4. **Given** a team of 70 active members, **When** the adaptive profile is used,
   **Then** the resolved profile name is "fast".
5. **Given** a team of 20 members run with each explicit profile (fast, balanced,
   optimal) in separate runs, **When** solve times are compared, **Then** all three
   produce valid pairings, and optimal is not faster than fast for a problem of this size.

---

### Edge Cases

- What happens when the team size is exactly at an adaptive-profile threshold boundary
  (15, 16, 60, 61 members)?
- How does the fairness distribution behave when history_weight is very low but
  non-zero (e.g., 0.1)?
- How does solve time behave when all team members share one timezone vs. when
  every member is in a unique timezone?
- What happens to memory metrics when an infeasibility is detected (no valid pairing
  exists due to avoidance constraints)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The test suite MUST include timing tests for team sizes covering small
  (≤ 15), medium (16–60), and large (> 60) active members, with separate cases for
  odd and even counts.
- **FR-002**: Each timing test MUST assert that solve time is below a documented
  per-size threshold and MUST fail if the threshold is exceeded.
- **FR-003**: The test suite MUST verify that `peak_memory_mb` and `memory_delta_mb`
  are populated and positive after every successful solve.
- **FR-004**: Memory scaling tests MUST demonstrate that a larger team produces a
  memory_delta_mb greater than or equal to that of a smaller team under the same conditions.
- **FR-005**: The test suite MUST include a memory upper-bound assertion for a
  50-member team with full history, asserting on ``memory_delta_mb`` (incremental
  solver allocation, test-order-independent) rather than ``peak_memory_mb``
  (absolute process RSS, which varies with test execution order). Bound: ≤ 5 MB
  (measured at 0.66–0.89 MB; ~6× headroom).
- **FR-006**: Fairness tests MUST simulate at least 10 consecutive rounds, updating
  history after each round, and MUST assert that pairwise meeting counts have a
  standard deviation ≤ 0.5 and max-gap ≤ 1 when history_weight > 0.
- **FR-007**: Fairness tests MUST include sit-out rotation verification for odd-sized
  teams, asserting no member sits out more than twice in 11 rounds for an 11-member team.
- **FR-008**: The test suite MUST include a negative fairness test confirming that
  with history_weight = 0 the fair-distribution guarantee is not asserted (the
  test passes regardless of distribution, documenting the precondition).
- **FR-009**: Solver-profile tests MUST verify that the adaptive profile resolves to
  the correct concrete profile name at each team-size threshold (N ≤ 15 → optimal,
  16–60 → balanced, > 60 → fast).
- **FR-010**: All performance tests MUST be tagged or marked so they can be run
  separately from the unit tests (e.g., excluded from a fast unit-test run).
- **FR-011**: Tests MUST use deterministic synthetic teams (fixed seeds or structured
  name/timezone generation) to ensure reproducibility.
- **FR-012**: Fairness tests MUST work with the existing history update mechanism,
  not bypass or mock it, so results reflect real solver behaviour.

### Key Entities

- **Test team**: A synthetically generated list of active team members with defined
  names and timezone strings used as solver input.
- **Round**: A single scheduler run followed by a history update reflecting the
  pairs produced; multiple rounds constitute a fairness simulation.
- **Fairness metric**: A computed statistic (standard deviation, max-minus-min) over
  per-pair meeting counts or per-person sit-out counts across all rounds.
- **Solve time**: Wall-clock elapsed time from the moment the solve call is made to
  the moment the result is returned, measured in seconds.
- **Memory delta**: The difference in process resident memory between the start and
  end of a single solve, in megabytes, as reported by the result object.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All timing tests pass consistently in CI; no team-size threshold is
  exceeded in 3 consecutive runs on standard CI hardware.
- **SC-002**: Fairness simulation of 10+ rounds on a 20-member team produces a
  standard deviation of pairwise meeting counts ≤ 0.5 in every run (deterministic
  due to structured, seed-free team generation; 0.5 is the theoretical minimum for
  integer counts at this round/team-size combination).
- **SC-003**: Memory metrics are populated and within expected bounds
  (``memory_delta_mb`` < 5 MB for a 50-member full-history run) across 3
  consecutive runs and regardless of test execution order.
- **SC-004**: The adaptive profile resolves to the correct name at each documented
  threshold; this is verified by 4 specific tests covering boundary conditions
  (N = 15, 16, 60, 61).
- **SC-005**: The overall test suite coverage for the solver and history modules does
  not decrease after adding these tests (gate remains at ≥ 80%).
- **SC-006**: Performance and fairness tests are runnable independently of the unit
  and integration suites via a single marker-based filter, completing the isolated
  run within 3 minutes on standard CI hardware.

## Assumptions

- The fairness simulation tests treat the existing `PairingHistory` and `solve_pairing`
  APIs as stable; no new public interfaces are needed.
- Timing thresholds are based on observed solve times from the previous
  buddy-scheduler implementation (30 members < 10 s, 50 members < 30 s, 100 members
  < 5 s with FAST/adaptive) and are tuned for the CBC solver on typical CI hardware.
- Memory bound (``memory_delta_mb`` < 5 MB for a 50-member run) is derived from
  the measured delta of 0.66–0.89 MB with ~6× headroom. ``peak_memory_mb``
  (absolute process RSS) is not used for the bound because its value depends on
  test execution order; ``memory_delta_mb`` is test-order-independent.
- Fairness assertions (std-dev ≤ 0.5, max-gap ≤ 1 over ≥ 10 rounds) represent the
  theoretical minimum for integer-valued distributions at these round/team-size
  combinations; the solver achieves this minimum. Assumes history_weight ≥ 1.0;
  lower weights may not yield fair distributions and are out of scope.
- All synthetic teams use structured (not random) member names and timezone strings to
  guarantee reproducibility without an explicit RNG seed.
