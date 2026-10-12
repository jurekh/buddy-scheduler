# Research: Performance and Fairness Tests

**Branch**: `004-performance-fairness-tests`
**Phase**: 0 — Outline & Research

---

## Decision 1: Test marker strategy

**Decision**: Use the existing `@pytest.mark.slow` marker for all tests in the new
`tests/performance/` module.

**Rationale**: `pyproject.toml` already configures `addopts = "-m 'not slow'"`,
which excludes slow-marked tests from every default `pytest` run. The `benchmark`
marker is also registered but is **not** excluded by default, so it cannot satisfy
FR-010 ("excluded from a fast unit-test run") without a `pyproject.toml` change.
Using `slow` requires no `pyproject.toml` modification and is consistent with the
existing convention.

**How to run performance tests explicitly**: `cd src && pytest -m slow`

**Alternatives considered**:
- Use `benchmark` marker and update `addopts` to `'not slow and not benchmark'` —
  works but requires changing `pyproject.toml` and risks confusion about two separate
  exclusion markers. Rejected in favour of the simpler single-marker approach.
- No marker, separate test directory excluded via `testpaths` override — fragile,
  non-standard. Rejected.

---

## Decision 2: Test file layout

**Decision**: Add a new `tests/performance/` subdirectory with four test files and
a shared `conftest.py`.

```
tests/performance/
  __init__.py
  conftest.py        ← make_team() helper; simulate_rounds() helper
  test_timing.py     ← wall-clock thresholds for each team-size band
  test_memory.py     ← peak_memory_mb and memory_delta_mb assertions
  test_fairness.py   ← multi-round pairing distribution tests
  test_profiles.py   ← adaptive profile resolution and monotonicity
```

**Rationale**: Separating by concern (timing / memory / fairness / profiles) keeps
each file focused and allows selective runs. A `conftest.py` centralises the
synthetic-team builder and round-simulator so they are not duplicated across files.
This matches the pattern in the existing `tests/unit/`, `tests/integration/`, and
`tests/contract/` directories.

**Alternatives considered**:
- Single `test_performance.py` at `tests/` root — harder to maintain and run
  selectively. Rejected.
- Put tests in `tests/integration/` — wrong; these are not end-to-end pipeline
  tests. Rejected.

---

## Decision 3: Fairness metric implementation

**Decision**: Compute fairness from the `PairingHistory.matrix` accumulated over N
rounds. Two metrics are used:

1. **Pairwise std-dev**: For all (i, j) pairs where i < j, collect the meeting
   count from `history.get_pair_count(i, j)`. Compute population standard deviation
   using `statistics.pstdev()` from the stdlib. Assert ≤ 0.5 after ≥ 10 rounds.
2. **Max-gap**: `max(counts) - min(counts)`. Assert ≤ 1 for the 10-member 15-round case.
3. **Sit-out spread**: Read `history.sit_out_counts`. For odd-sized teams of N
   members simulated over N rounds, assert `max(sit_out_counts.values()) ≤ 2`.

**Rationale**: `statistics.pstdev` is stdlib (no extra dep). Population std-dev
(not sample) is appropriate because we enumerate the entire pair space, not a
sample. The 0.5 threshold is the theoretical minimum for integer-valued counts at
these round/team-size combinations: with N=10 and 15 rounds, expected mean is
1.667 meetings/pair so counts must be 1 or 2, giving minimum std-dev of
√(2/3 × 1/3) ≈ 0.471; with N=20 and 10 rounds, counts are 0 or 1, minimum
std-dev ≈ 0.499. Empirical measurement confirms the solver achieves this minimum
deterministically across repeated runs.

**Alternatives considered**:
- Gini coefficient — more complex, no stdlib support. Rejected.
- Max-minus-min spread — easy but sensitive to outliers in large teams. Used as a
  secondary check (≤ 2) for the 10-member 15-round test, not as the primary metric.

---

## Decision 4: Round simulation pattern

**Decision**: Each "round" in fairness tests is executed as:
```
result = solve_pairing(members, history_weight, tz_weight, history, set(), profile)
for a, b in result.pairs:
    history.increment_pair(a, b)
if result.sitting_out:
    history.increment_sit_out(result.sitting_out)
```
The same `PairingHistory` instance is mutated in place across rounds. No file I/O
is involved, so atomicity and locking requirements from Constitution Principle II
do not apply.

**Rationale**: This is the minimal faithful simulation of production behaviour.
The history object is modified using the same public methods the CLI uses, satisfying
FR-012 ("work with the existing history update mechanism, not bypass or mock it").

---

## Decision 5: Timing thresholds

**Decision**: Per-size wall-clock thresholds (using `time.monotonic()`):

| Team size (active) | Profile (adaptive) | Threshold |
|--------------------|--------------------|-----------|
| ≤ 15               | optimal            | 30 s      |
| 30 even            | balanced           | 10 s      |
| 35 odd             | balanced           | 15 s      |
| 50 even            | balanced           | 30 s      |
| 100 even           | fast               | 5 s       |

**Rationale**: Thresholds are derived from observed solve times in the earlier
`buddy-scheduler` implementation (test_performance.py) with a 2× safety margin to
account for CI hardware variance. The N=100 threshold (5 s) is already validated by
`tests/unit/test_mip.py::test_performance_100_members` and is kept consistent.
Optimal-profile tests (N ≤ 15) are allowed up to 30 s because the OPTIMAL config
uses a 300 s CBC time limit internally; the test verifies the solver terminates well
inside that budget on a small problem.

**Alternatives considered**:
- Tighter thresholds (e.g., 2 s for N=30) — would produce flaky failures on slow
  CI runners. Rejected.
- No upper bound, only smoke-test — does not satisfy FR-002. Rejected.

---

## Decision 6: Deterministic team generation

**Decision**: Synthetic teams are generated without `random` by using structured
naming and cycling through a fixed timezone list:

```python
TIMEZONES = ["UTC", "America/New_York", "Europe/London", "Asia/Tokyo",
             "America/Los_Angeles", "Asia/Kolkata"]
members = [
    TeamMember(name=f"Member{i:03d}", timezone=TIMEZONES[i % len(TIMEZONES)])
    for i in range(n)
]
```

**Rationale**: No RNG seed management needed. Tests are reproducible across Python
versions and platforms. Satisfies FR-011.

---

## Decision 7: Memory upper-bound assertion

**Decision**: Assert `peak_memory_mb < 50` for a 50-member fully-populated history
run. This is the FR-005 bound.

**Rationale**: Measured peak RSS in this implementation is ~23.4 MB (stable to
< 0.2 MB across 5 consecutive runs). The 50 MB ceiling is a ~2× safety margin,
sufficient to absorb GC variance and CI hardware differences while still catching
meaningful regressions. The earlier estimate of 40–60 MB (from the reference
buddy-scheduler implementation) was not measured against this codebase and produced
an inflated 200 MB bound that would only catch catastrophic failures.

**Alternatives considered**:
- No upper bound — does not satisfy FR-005. Rejected.
- 100 MB — still catches regressions but gives 4× margin; 2× is sufficient given
  the measured stability. Rejected in favour of 50 MB.
- 200 MB — original estimate; ~8.5× the actual value, too loose to be meaningful.
  Rejected after empirical measurement.

---

## Decision 8: No new contracts or public interfaces

**Decision**: This feature adds only test code. No new public CLI flags, JSON output
fields, YAML schema changes, or Python public APIs are introduced.

**Rationale**: The feature specification explicitly states: "The fairness simulation
tests treat the existing `PairingHistory` and `solve_pairing` APIs as stable; no new
public interfaces are needed." Therefore the `contracts/` directory is omitted from
this plan's Phase 1 output.
