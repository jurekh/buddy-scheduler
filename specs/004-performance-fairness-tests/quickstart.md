# Quickstart: Running Performance and Fairness Tests

**Branch**: `004-performance-fairness-tests`

---

## Run only performance and fairness tests

```bash
cd src
pytest -m slow -v
```

These tests are excluded from the default `pytest` run (they carry `@pytest.mark.slow`).
Running with `-v` shows individual test names, solve times, and memory figures.

## Run the default test suite (excludes performance tests)

```bash
cd src
pytest
```

Performance tests are excluded automatically. Use this to verify that the new tests
do not affect existing coverage or correctness.

## Run with coverage

```bash
cd src
pytest --cov=buddy_scheduler --cov-report=term-missing
```

Coverage must remain ≥ 80% after this feature is merged (SC-005).

## Run a specific performance test file

```bash
cd src
pytest -m slow tests/performance/test_timing.py -v
pytest -m slow tests/performance/test_memory.py -v
pytest -m slow tests/performance/test_fairness.py -v
pytest -m slow tests/performance/test_profiles.py -v
```

## Run the adaptive profile threshold tests (fast, no solver invocation needed)

Profile resolution tests that only check the threshold logic (not full solves) are
also marked `slow` for consistency, but complete in under a second:

```bash
cd src
pytest -m slow tests/performance/test_profiles.py::TestAdaptiveProfileResolution -v
```

## Expected runtime

| Test file           | Approx. duration |
|---------------------|-----------------|
| test_timing.py      | 60–120 s        |
| test_memory.py      | 30–60 s         |
| test_fairness.py    | 60–180 s        |
| test_profiles.py    | 30–90 s         |
| **Total**           | **3–7 min**     |

SC-006 requires the full isolated run to complete within 3 minutes on standard CI
hardware. If the CI runner is faster than a developer laptop, the suite may fit
within the budget; CI-specific thresholds can be adjusted in `test_timing.py` via
module-level constants if needed.
