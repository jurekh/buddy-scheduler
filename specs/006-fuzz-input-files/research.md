# Research: Fuzz Testing for Team Roster and History Files

**Branch**: `006-fuzz-input-files`
**Created**: 2026-03-03

---

## Decision 1: Property-based testing library

**Decision**: Use `hypothesis >= 6.0` (latest stable: 6.151.9 as of 2026-02-16).

**Rationale**:
- Integrates natively with pytest via `@given` + `@settings` decorators — no test runner changes.
- Provides deterministic seed control (`--hypothesis-seed=N` CLI option), automatic
  counterexample shrinking, and a configurable per-example deadline (`deadline=timedelta(...)`).
- Covers all corpus categories required by the spec: `st.binary()` for random bytes,
  `st.text()` for Unicode, `st.recursive()` for deep nesting, `st.one_of()` for combining
  generators, `st.lists(...).map(yaml.dump)` for structured YAML.
- Zero new runtime dependencies — hypothesis is dev-only.

**Alternatives considered**:
- `atheris` (Google coverage-guided fuzzer): requires clang/LLVM build toolchain, produces
  large native dependencies; overkill for validating Python exception contracts.
- Hand-crafted parametrized tests: cannot generate boundary cases automatically and cannot
  shrink failures to a minimal reproducer.
- `mutmut` (mutation testing): tests code quality, not input safety — different goal.

---

## Decision 2: Timeout per generated input

**Decision**: Use `@settings(deadline=timedelta(seconds=5))` on all fuzz test methods.

**Rationale**: hypothesis measures wall-clock time per example and raises
`hypothesis.errors.DeadlineExceeded` (a test failure) if the time is exceeded. This
satisfies FR-008 ("hang = not returning within 5 seconds") without external process
management. `DeadlineExceeded` is treated identically to an assertion failure — hypothesis
shrinks the input and reports it.

**CI note**: Disk I/O in temp directories on shared CI runners can occasionally spike to
200–500 ms. A 5-second budget is 10–25× above typical parse time (< 100 ms), which makes
false positives from I/O jitter unlikely. If a specific CI environment shows flakiness,
the timeout can be relaxed to `deadline=timedelta(seconds=10)` without changing the spec.

**Alternatives considered**:
- `deadline=None`: removes timeout enforcement entirely — violates FR-008.
- External `subprocess` timeout: adds complexity; not needed since loaders are pure Python.

---

## Decision 3: Deterministic seed and reproducibility

**Decision**: Pass `database=None` in `@settings` and use `--hypothesis-seed=N` at the
pytest CLI for reproducible runs.

**Rationale**:
- `database=None` disables the hypothesis example database (`.hypothesis/examples/`),
  ensuring each run is driven purely by the seed rather than by previously-persisted
  failures. Committing `.hypothesis/` to version control is impractical.
- `--hypothesis-seed=42 pytest -m slow` produces an identical sequence of examples on
  every machine with every invocation, satisfying FR-005.
- When hypothesis reports a failure it prints `Falsifying example ...` and the seed
  used; re-running with `--hypothesis-seed=<that seed>` reproduces the failure exactly.

**Alternatives considered**:
- `@seed(N)` decorator in source: hardcodes a single seed forever; prevents exploratory
  runs from finding new failures.
- `settings(derandomize=True)`: seed derived from test name + source hash — changes
  whenever the test body is edited, hindering failure reproduction.

---

## Decision 4: File writing approach inside `@given` tests

**Decision**: Use `suppress_health_check=[HealthCheck.function_scoped_fixture]` with the
standard pytest `tmp_path` fixture.

**Rationale**:
- `tmp_path` is function-scoped — created once per test function, shared across all
  100 generated examples. Each example overwrites the same file path (e.g.,
  `tmp_path / "roster.yaml"`) and reads it back immediately. This is safe and correct.
- `suppress_health_check` is the documented hypothesis mechanism for explicitly opting
  into function-scoped fixtures. It does not disable any safety checking on the code
  under test.
- The `tmp_path` approach keeps teardown automatic (pytest cleans up the directory),
  avoiding manual `unlink` calls that could leak temp files on test failure.

**Alternatives considered**:
- `tempfile.NamedTemporaryFile` inline: works but requires manual `unlink` in a
  `finally` block; more boilerplate and more risk of temp file leaks if the `finally`
  path is not exercised (e.g., `KeyboardInterrupt`).

---

## Decision 5: YAML `safe_load` enforcement (FR-006)

**Decision**: Add a deterministic (non-fuzz) parametrized test for Python-specific YAML
tags. Do NOT mark it `@pytest.mark.slow` so it always runs in the default test suite.

**Rationale**: `yaml.safe_load` uses `SafeLoader`, which registers no Python-specific
constructors. Any `!!python/object`, `!!python/object/apply`, `!!python/object/new`,
`!!python/name`, or `!!python/tuple` tag raises `yaml.constructor.ConstructorError`
(subclass of `yaml.YAMLError`), which the existing `except yaml.YAMLError` clause in
`validator.py` converts to `FileLoadError`. This is guaranteed by the SafeLoader design
and has been true across all PyYAML releases.

Tags to test (representative, not exhaustive):
- `!!python/object/apply:os.system ['id']` — most dangerous tag (RCE)
- `!!python/object/new:subprocess.Popen [['id']]` — alternative RCE vector
- `!!python/tuple [1, 2, 3]` — less dangerous but still rejected
- `!!python/name:os.getcwd` — attribute reference

---

## Decision 6: Hypothesis strategies corpus structure

**Decision**: Use `st.one_of()` to combine strategies into a single corpus per loader.
Use `st.recursive()` for deeply nested JSON structures. Use `st.lists(...).map(yaml.dump)`
for structured YAML that exercises member-field validation.

**Corpus per loader — team roster**:
| Strategy | Coverage target |
|----------|----------------|
| `st.binary()` | Non-UTF-8 bytes, binary noise |
| `st.text()` | Arbitrary Unicode text |
| `st.just("")` | Empty file edge case |
| `st.just("null")` | YAML null root |
| `st.just("{}")` | YAML mapping root (not a list) |
| `st.text(min_size=10_001)` | Very long string (> 10 000 chars) |
| `st.binary(min_size=1_048_577)` | Large binary (> 1 MB) |
| Python-tag strings | YAML unsafe-tag inputs |
| `st.lists(member_dict, ...).map(yaml.dump)` | Valid-looking but semantically varied YAML |

**Corpus per loader — history file**:
| Strategy | Coverage target |
|----------|----------------|
| `st.binary()` | Non-UTF-8 bytes |
| `st.text()` | Arbitrary Unicode text |
| `st.just("null")` | JSON null root |
| `st.just("[]")` | JSON array root |
| `st.just("{}")` | Empty JSON object |
| `st.text(min_size=10_001)` | Very long string |
| `st.binary(min_size=1_048_577)` | Large binary (> 1 MB) |
| `st.recursive(...).map(json.dumps)` | Nested JSON including deep structures |
| Structured `pair_counts`/`sit_out_counts` dict | Semantic validation paths |

---

## Decision 7: CLI fuzz test strategy (US3)

**Decision**: Two separate `@given` test methods — one fuzzing `--team`, one fuzzing
`--history`. Both use `CliRunner.invoke(main, [...])` from Click's testing utilities.

**Approach**:
- For `--team` fuzz: write generated content to a temp file, call
  `runner.invoke(main, ["--team", str(path)])`, assert `exit_code in (0, 1)`.
- For `--history` fuzz: use a fixed valid team file; write generated content to a second
  temp file for `--history`, assert same contract.
- If `exit_code != 0`: assert `json.loads(result.stdout)["success"] is False` and
  `"error" in data` (FR-007).

**Rationale**: This closes the gap between the library layer (US1/US2) and the process
boundary (US3). The CLI wrapper catches all `BuddySchedulerError` subclasses and writes
a JSON error body — the fuzz test verifies that contract holds for any file content.

---

## Decision 8: New files — no production code changes

**Decision**: Zero changes to `src/`. New files:
- `tests/fuzz/__init__.py` (empty)
- `tests/fuzz/test_fuzz_loaders.py` (all fuzz + safe_load tests)
- `pyproject.toml`: add `hypothesis>=6.0` to `[dependency-groups].dev`

**Rationale**: The production loaders already satisfy the safety contract (FR-001/FR-002).
The purpose of this feature is to verify that contract automatically and catch any future
regressions (SC-005). No new production code is needed.

---

## Assumptions confirmed

- `@pytest.mark.slow` is already registered in `pyproject.toml` (`addopts = "-m 'not slow'"`)
  — fuzz tests in this marker are excluded from the default `pytest` run automatically.
- `hypothesis` is a dev-only dependency; it does not appear in `[project].dependencies`.
- Coverage gate (≥ 80%) will not be breached: fuzz tests add coverage to existing modules,
  and hypothesis tests are counted by `pytest-cov` like any other tests.
- `uv` manages the lock file; after adding `hypothesis` to `pyproject.toml`, running
  `uv lock` and committing `uv.lock` is part of the delivery.
