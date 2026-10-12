# Implementation Plan: Fuzz Testing for Team Roster and History Files

**Branch**: `006-fuzz-input-files` | **Date**: 2026-03-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-fuzz-input-files/spec.md`

## Summary

Add property-based fuzz tests verifying that the team roster and history file loaders
never raise unhandled exceptions for any input. For every generated input — random bytes,
adversarial YAML/JSON, Unicode edge cases, deeply nested structures, large files — each
loader must either return a valid result or raise `FileLoadError` or
`DataValidationError`. A third test suite verifies the CLI always exits with code 0 or 1.

One new dev dependency (`hypothesis >= 6.0`) and one new test module
(`tests/fuzz/test_fuzz_loaders.py`) are added. No production code changes are required.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: hypothesis ≥ 6.0 (new dev dep); existing: PyYAML ≥ 6.0,
pydantic ≥ 2.0, Click ≥ 8.1 — all unchanged
**Storage**: N/A — tests write to `tmp_path` (pytest fixture); no persistent state
**Testing**: pytest + hypothesis (`@given`, `@settings`), `@pytest.mark.slow` marker,
`--hypothesis-seed=N` for deterministic runs
**Target Platform**: Linux (CI), developer workstations
**Project Type**: Test suite extension — zero production code changes
**Performance Goals**: Full fuzz corpus (≥ 100 examples × 4 test methods + 1 CLI method)
completes within 3 minutes on standard CI hardware (SC-004)
**Constraints**: ≤ 5 seconds per generated input (`hypothesis` deadline = FR-008);
zero new runtime dependencies
**Scale/Scope**: ≥ 100 generated inputs per loader per run (FR-003)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Type Safety & Validated Inputs | ✅ PASS | Assertions use `isinstance(exc, (FileLoadError, DataValidationError))`; pytest.fail names the actual type |
| II. Data Integrity | ✅ N/A | Feature is test-only; no persistent writes |
| III. Comprehensive Testing | ✅ PASS | `@pytest.mark.slow` gates fuzz tests from the default run; coverage gate ≥ 80% preserved (FR-009); hypothesis improves branch coverage of validation paths |
| IV. Transparent Operations | ✅ N/A | No new CLI output |
| V. Explicit Failure Reporting | ✅ PASS | Any unexpected exception causes `pytest.fail(f"Unexpected {type(exc).__name__}: {exc}")` — typed, actionable |

No violations. Complexity Tracking section omitted.

## Project Structure

### Documentation (this feature)

```text
specs/006-fuzz-input-files/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── checklists/
│   └── requirements.md
└── tasks.md             ← /speckit.tasks output (not yet generated)
```

### Source Code (repository root)

```text
tests/
├── fuzz/
│   ├── __init__.py                ← NEW (empty)
│   └── test_fuzz_loaders.py       ← NEW (all fuzz + safe_load tests)
├── contract/                      ← unchanged
├── integration/                   ← unchanged
├── performance/                   ← unchanged
└── unit/                          ← unchanged

pyproject.toml                     ← add hypothesis>=6.0 to [dependency-groups].dev
uv.lock                            ← regenerated after adding hypothesis
```

**Structure Decision**: Single test module in a new `tests/fuzz/` subdirectory to clearly
separate property-based tests from unit, contract, integration, and performance tests.
No changes to `src/`. All fuzz test methods use `@pytest.mark.slow`; the YAML safe-load
enforcement test does NOT use `@pytest.mark.slow` (it is fast and security-critical).

---

## Phase 0 research artifacts

See [research.md](research.md) for full decision rationale. Key decisions:

- **Library**: `hypothesis >= 6.0` — native pytest integration, strategies, deadline,
  seed control.
- **Timeout**: `deadline=timedelta(seconds=5)` — hypothesis raises `DeadlineExceeded`
  on breach, which counts as a test failure (FR-008).
- **Seed**: `database=None` in `@settings` + `--hypothesis-seed=N` at runtime (FR-005).
- **Fixture**: Use `tmp_path` with
  `suppress_health_check=[HealthCheck.function_scoped_fixture]` — shared temp dir across
  all 100 examples per test method; each example overwrites the same file path.
- **Corpus**: `st.one_of(st.binary(), st.text(), structured_strategies, large_inputs)`
  covers all categories in FR-003 / Assumptions.
- **No production changes**: Loaders already satisfy the safety contract.

---

## Phase 1 design artifacts

See [data-model.md](data-model.md) and [quickstart.md](quickstart.md).

### `tests/fuzz/test_fuzz_loaders.py` — module structure

```text
TestYamlSafeLoadEnforcement         ← deterministic (no @slow), parametrize Python tags
TestFuzzTeamRoster                  ← @pytest.mark.slow
  test_binary_content_never_crashes     @given(st.binary())
  test_text_content_never_crashes       @given(st.text())
  test_large_content_never_crashes      @given(st.binary(min_size=1_048_577))
  test_structured_yaml_never_crashes    @given(member_list_strategy)
TestFuzzHistory                     ← @pytest.mark.slow
  test_binary_content_never_crashes     @given(st.binary())
  test_text_content_never_crashes       @given(st.text())
  test_large_content_never_crashes      @given(st.binary(min_size=1_048_577))
  test_nested_json_never_crashes        @given(recursive_json_strategy)
TestFuzzCLI                         ← @pytest.mark.slow
  test_team_file_content_exit_zero_or_one   @given(st.binary())
  test_history_file_content_exit_zero_or_one  @given(st.binary())
```

### `@settings` profile (shared)

```python
_SLOW_SETTINGS = settings(
    max_examples=100,
    deadline=timedelta(seconds=5),
    database=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
```

### Corpus strategies

**Team roster** (`_ROSTER_CORPUS`):
```python
st.one_of(
    st.binary(),
    st.text(),
    st.just(""),
    st.just("null"),
    st.just("{}"),
    st.just("!!python/object/apply:os.system ['id']"),
    st.just("!!python/object/new:subprocess.Popen [['id']]"),
    st.just("!!python/tuple [1, 2, 3]"),
    st.text(min_size=10_001),           # > 10 000 chars
    st.binary(min_size=1_048_577),      # > 1 MB
    # Valid-looking YAML with generated member fields:
    st.lists(
        st.fixed_dictionaries({
            "name": st.text(min_size=0, max_size=128),
            "timezone": st.text(min_size=0, max_size=64),
            "active": st.booleans(),
            "avoid_buddies": st.lists(st.text(min_size=1), max_size=10),
        }),
        min_size=0, max_size=20,
    ).map(yaml.safe_dump),
)
```

**History** (`_HISTORY_CORPUS`):
```python
st.one_of(
    st.binary(),
    st.text(),
    st.just(""),
    st.just("null"),
    st.just("[]"),
    st.just("{}"),
    st.text(min_size=10_001),
    st.binary(min_size=1_048_577),
    # Arbitrary JSON (deeply nested via st.recursive):
    st.recursive(
        st.none() | st.booleans() | st.integers() | st.text(),
        extend=lambda xs: st.lists(xs) | st.dictionaries(st.text(), xs),
        max_leaves=500,
    ).map(json.dumps),
    # Structured history-like JSON with generated pair_counts / sit_out_counts:
    st.fixed_dictionaries({
        "pair_counts": st.dictionaries(
            st.text(min_size=1),
            st.dictionaries(st.text(min_size=1), st.integers()),
        ),
        "sit_out_counts": st.dictionaries(st.text(min_size=1), st.integers()),
    }).map(json.dumps),
)
```

### Safety assertion pattern

```python
try:
    result = load_team_roster(p)
    assert isinstance(result, list)
except (FileLoadError, DataValidationError):
    pass
except Exception as exc:
    pytest.fail(f"Unexpected {type(exc).__name__}: {exc}")
```

### CLI assertion pattern

```python
result = runner.invoke(main, ["--team", str(team_path)])
assert result.exit_code in (0, 1), (
    f"Unexpected exit code {result.exit_code}: {result.output!r}"
)
if result.exit_code != 0:
    data = json.loads(result.stdout)
    assert data["success"] is False
    assert "error" in data
```

---

## Post-design Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Type Safety | ✅ PASS | All exception checks are typed; `pytest.fail` includes the actual type name |
| II. Data Integrity | ✅ N/A | No writes to production state |
| III. Comprehensive Testing | ✅ PASS | ≥ 100 inputs per loader, `@pytest.mark.slow` gating, coverage preserved |
| IV. Transparent Operations | ✅ N/A | No new output |
| V. Explicit Failure Reporting | ✅ PASS | Unexpected exceptions surfaced with full type + message |
