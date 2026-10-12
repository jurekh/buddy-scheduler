# Research: Input Validation — Invalid Paths and Malformed Files

**Branch**: `005-input-validation-tdd`
**Phase**: 0 — Outline & Research

---

## Decision 1: Actual current behaviour for each missing case

**Decision**: Verified by reading production code (`validator.py`, `history.py`, `cli.py`)
before designing tests. All missing cases share a pattern: the error is propagated
to the CLI as a structured JSON failure (exit 1), but the error message is either
generic or absent.

| Case | Current behaviour | Missing |
|------|-------------------|---------|
| `--team` is a directory | `IsADirectoryError` caught by `OSError` handler → `FileLoadError("Cannot read team roster file …: [Errno 21] Is a directory")` → exit 1, JSON error | No specific `is_dir()` check; message includes "Is a directory" but only as OS text buried in the generic prefix. A dedicated check gives a cleaner user-facing message. |
| `--history` is a directory | Same as above via `history.py` | Same |
| `--history` is zero-byte | `json.loads("")` → `JSONDecodeError` → `FileLoadError("History file is not valid JSON: Expecting value…")` → exit 1 | No dedicated empty check; message mentions JSON not emptiness |
| `--history` is non-JSON text | `json.loads(raw)` → `JSONDecodeError` → `FileLoadError("History file is not valid JSON: …")` → exit 1 | Already handled correctly — needs test only |
| `--history` is JSON but wrong schema | `_HistoryModel.model_validate(data)` → Pydantic error → `DataValidationError("History validation failed: …")` → exit 1 | Already handled correctly — needs test only |
| `--history-weight 0.0` | `history_weight < 0.0` check passes → valid solve | Needs test only; logic is correct |
| `--tz-weight 0.0` | `tz_weight < 0.0` check passes → valid solve | Needs test only; logic is correct |
| `--history-weight "abc"` | Click `type=float` rejects at parse time → exit 2, Click usage error on stderr | Needs test only; behaviour is correct |
| `--tz-weight "abc"` | Same as above | Needs test only |

**Rationale**: Understanding actual behaviour before writing tests prevents writing
tests that assert the wrong thing. Most cases already work — the feature is
primarily about test coverage and minor message improvements.

---

## Decision 2: Production code changes required

**Decision**: Two targeted additions in `validator.py` and three in `history.py`.
No changes to `cli.py` or `models.py`.

**`src/buddy_scheduler/validator.py`** — `load_team_roster`:
```
# Add after exists check, before path.read_text():
if path.is_dir():
    raise FileLoadError(f"Team roster path is a directory, not a file: {path}")
```

**`src/buddy_scheduler/history.py`** — `load_history`:
```
# Add after exists check, before path.read_text():
if path.is_dir():
    raise FileLoadError(f"History path is a directory, not a file: {path}")

# Add after raw = path.read_text(), before json.loads(raw):
if not raw.strip():
    raise FileLoadError(f"History file is empty: {path}")
```

**Rationale**: Each change is one or two lines inserted at the natural early-exit
point, consistent with the existing guard pattern in both loaders. No new exception
types, no new abstraction layers.

**Alternatives considered**:
- Catch `IsADirectoryError` specifically instead of adding `is_dir()` — works
  but produces platform-dependent errno messages. An explicit guard is clearer and
  platform-independent. Rejected.
- Add a shared path-validation utility function — unnecessary abstraction for
  two identical two-line guards. Rejected.

---

## Decision 3: Test placement strategy

**Decision**: Tests split across two files following the existing separation of concerns:

| Test | File | Class |
|------|------|-------|
| `load_team_roster` with directory path | `tests/unit/test_validator.py` | `TestFileAccessErrors` |
| `load_history` with directory path | `tests/unit/test_history.py` | `TestLoadHistory` |
| `load_history` with zero-byte file | `tests/unit/test_history.py` | `TestLoadHistory` |
| `load_history` with non-JSON content | `tests/unit/test_history.py` | `TestLoadHistory` |
| `load_history` with wrong JSON schema | `tests/unit/test_history.py` | `TestLoadHistory` |
| CLI `--team` directory → exit 1 | `tests/contract/test_cli_contract.py` | `TestExitCodes` |
| CLI `--history` directory → exit 1 | `tests/contract/test_cli_contract.py` | `TestHistoryFlags` |
| CLI `--history` non-JSON → exit 1 | `tests/contract/test_cli_contract.py` | `TestHistoryFlags` |
| CLI `--history-weight 0.0` → exit 0 | `tests/contract/test_cli_contract.py` | `TestExitCodes` |
| CLI `--tz-weight 0.0` → exit 0 | `tests/contract/test_cli_contract.py` | `TestExitCodes` |
| CLI `--history-weight "abc"` → non-zero | `tests/contract/test_cli_contract.py` | `TestExitCodes` |
| CLI `--tz-weight "abc"` → non-zero | `tests/contract/test_cli_contract.py` | `TestExitCodes` |

**Rationale**: Unit tests assert on the exception type and message raised by the
library functions directly. Contract tests assert on the CLI exit code and JSON
output. This mirrors the existing structure and means each layer is tested
independently. No new test files are needed.

---

## Decision 4: TDD interpretation for this feature

**Decision**: The TDD order is:
1. Write the test(s) for a missing case.
2. Run the test suite to establish which tests are RED (fail) vs GREEN (pass).
3. For RED tests: make the minimal production-code change to turn them GREEN.
4. For GREEN tests on the first run: the behaviour already exists — the test
   documents it and prevents future regression.
5. Repeat until all new tests are GREEN with no regressions.

**Rationale**: The spec states "failing test first, minimal fix, passing test
confirms the fix." In practice, several cases (non-JSON history, wrong schema,
weight boundaries, non-numeric strings) are already handled by existing code. For
those, the TDD cycle is write-test → run (GREEN) → done. For cases requiring new
code (is_dir checks, empty history message), the cycle is write-test → run (RED)
→ add guard → run (GREEN).

**Alternatives considered**:
- Artificially break production code to make all tests RED first — defeats the
  purpose and obscures which cases genuinely need fixes. Rejected.

---

## Decision 5: Non-numeric weight strings — JSON output contract

**Decision**: Tests for `--history-weight "abc"` and `--tz-weight "abc"` assert
only that the exit code is non-zero; they do NOT assert a JSON error body.

**Rationale**: Click's `type=float` rejects non-numeric strings at argument
parsing time before the CLI's error-handling wrapper runs. The output is a Click
usage error on stderr (not stdout), and the exit code is 2. The existing JSON
error contract applies only to errors caught inside the `main()` function's
try/except block. Asserting a JSON body for argument-parsing errors would require
overriding Click's default error handling — that is a separate design decision
beyond this feature's scope.

---

## Decision 6: No new fixtures or conftest needed

**Decision**: All new tests use `tmp_path` (built-in pytest fixture) and the
existing `CliRunner` helper pattern from `test_cli_contract.py`. No new
`conftest.py` or shared fixture functions are required.

**Rationale**: The existing helper functions `_write_team()`, `_valid_team()`, and
`_parse()` in `test_cli_contract.py` already cover common setup needs. New tests
can use `tmp_path` directly.
