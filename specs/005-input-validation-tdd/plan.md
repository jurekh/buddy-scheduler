# Implementation Plan: Input Validation — Invalid Paths and Malformed Files

**Branch**: `005-input-validation-tdd` | **Date**: 2026-03-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-input-validation-tdd/spec.md`

## Summary

Add test coverage for previously untested CLI boundary conditions (directory paths,
malformed history files, weight parameter boundaries), and make two minimal
production-code fixes in the team and history loaders so that directory-as-path
produces a specific, user-friendly error message rather than an OS errno string.
All changes follow TDD order: test written first, run to observe RED/GREEN, then
minimal fix applied for RED cases.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: pytest ≥ 7.0, Click ≥ 8.1 (CliRunner), Pydantic v2,
  PyYAML ≥ 6.0 — all already in `pyproject.toml`; no new dependencies
**Storage**: N/A — tests operate in memory and `tmp_path`; no new file I/O patterns
**Testing**: pytest + pytest-cov; all new tests excluded from `@pytest.mark.slow`
  (default run only)
**Target Platform**: Linux CI (same as existing tests)
**Project Type**: CLI tool — test additions + two targeted production-code fixes
**Performance Goals**: N/A — no solver calls; all new tests complete in milliseconds
**Constraints**: Coverage gate ≥ 80% must be maintained; no new public interfaces
**Scale/Scope**: 12 new test cases across 3 existing test files; 3 new production
  code lines across 2 existing source files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment | Status |
|-----------|------------|--------|
| I. Type Safety | No new public interfaces; existing typed exception hierarchy used throughout; no new types introduced | ✅ N/A |
| II. Data Integrity | No new persistent state; existing atomic-write pattern unchanged | ✅ N/A |
| III. Comprehensive Testing | **Key gate**: New tests cover boundary and error conditions; all tests run in default suite (no `slow` marker); coverage gate enforced | ✅ Satisfied |
| IV. Transparent Operations | New error messages are written to stdout as JSON, consistent with the existing contract (Principle IV) | ✅ Satisfied |
| V. Explicit Failure Reporting | The two new `is_dir()` guards and the empty-file guard in the history loader report failures before computation begins, consistent with Principle V | ✅ Satisfied |
| Code Quality | ruff + mypy must pass; no new public functions (only guards inside existing ones); no docstring changes needed for the guards | ✅ Required |

**No violations. No complexity tracking needed.**

## Project Structure

### Documentation (this feature)

```text
specs/005-input-validation-tdd/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks — not yet created)
```

### Source Code (repository root)

```text
src/buddy_scheduler/
├── validator.py         # +1 is_dir guard in load_team_roster
└── history.py           # +1 is_dir guard + 1 empty-file guard in load_history

tests/
├── unit/
│   ├── test_validator.py  # +1 test case
│   └── test_history.py    # +4 test cases
└── contract/
    └── test_cli_contract.py  # +7 test cases
```

**Structure Decision**: Single project layout (existing layout). No new files.
All changes are additions to existing test and source files.

## Phase 0: Research

All unknowns resolved. See [research.md](research.md) for full decision log.

Key findings:
- Most missing cases are already handled by existing code — tests are the primary
  gap. Two cases need minimal production code fixes: `is_dir()` checks in both
  loaders, and an explicit empty-file check in `load_history`.
- No new exception types, helper functions, or test files are needed.
- `@pytest.mark.slow` is NOT used — all new tests run in the default suite.
- TDD cycle: write test → run (RED or GREEN) → fix if RED → re-run.

## Phase 1: Design

See [data-model.md](data-model.md) for the complete validation rule tables.
See [quickstart.md](quickstart.md) for how to run tests and verify outputs manually.

No `contracts/` directory needed — this feature adds no new public interfaces.

### File-by-file design notes

#### `src/buddy_scheduler/validator.py`

One guard added in `load_team_roster`, after the `exists` check, before
`path.read_text()`:

```python
if path.is_dir():
    raise FileLoadError(
        f"Team roster path is a directory, not a file: {path}"
    )
```

#### `src/buddy_scheduler/history.py`

Two guards added in `load_history`:

1. After the `exists` check, before `path.read_text()`:
```python
if path.is_dir():
    raise FileLoadError(
        f"History path is a directory, not a file: {path}"
    )
```

2. After `raw = path.read_text(...)`, before `json.loads(raw)`:
```python
if not raw.strip():
    raise FileLoadError(f"History file is empty: {path}")
```

#### `tests/unit/test_validator.py` — class `TestFileAccessErrors`

New test:

| Test | Input | Expected |
|------|-------|----------|
| `test_team_path_is_directory` | `path = tmp_path` (a directory) | `FileLoadError` matching `"directory"` |

#### `tests/unit/test_history.py` — class `TestLoadHistory`

New tests:

| Test | Input | Expected |
|------|-------|----------|
| `test_directory_path_raises_file_load_error` | `path = tmp_path` | `FileLoadError` matching `"directory"` |
| `test_zero_byte_file_raises_file_load_error` | empty file | `FileLoadError` matching `"empty"` |
| `test_json_array_root_raises_data_validation` | `[1, 2, 3]` | `DataValidationError` |
| `test_json_null_root_raises_data_validation` | `null` | `DataValidationError` (or `FileLoadError`) |

#### `tests/contract/test_cli_contract.py`

New tests added to existing classes:

**Class `TestExitCodes`**:

| Test | Flag and value | Expected exit code |
|------|---------------|--------------------|
| `test_team_directory_exits_one` | `--team <tmpdir>` | 1 |
| `test_history_weight_zero_exits_zero` | `--history-weight 0.0` | 0 |
| `test_tz_weight_zero_exits_zero` | `--tz-weight 0.0` | 0 |
| `test_history_weight_non_numeric_exits_nonzero` | `--history-weight high` | non-zero |
| `test_tz_weight_non_numeric_exits_nonzero` | `--tz-weight medium` | non-zero |

**Class `TestHistoryFlags`** (new sub-section for error paths):

| Test | Setup | Expected |
|------|-------|----------|
| `test_history_directory_exits_one` | `--history <tmpdir>` | exit 1, JSON error |
| `test_history_non_json_exits_one` | `--history` → file with text content | exit 1, JSON error |

Each new CLI test that expects exit 1 also asserts:
- `stdout` parses as JSON
- `data["success"] is False`
- `"error"` key is present and non-empty
