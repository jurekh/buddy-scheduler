# Tasks: Input Validation — Invalid Paths and Malformed Files

**Input**: Design documents from `/specs/005-input-validation-tdd/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**TDD**: Tests are written first and run before any production-code change. Some
tests will be GREEN on first run (existing behaviour documented); others will be
RED until the corresponding production-code fix is applied. Both outcomes are
correct TDD — RED means fix needed, GREEN means behaviour already exists.

**Organization**: Tasks are grouped by user story. Each story is independently
testable after its phase completes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story this task belongs to

---

## Phase 1: Setup

**Purpose**: Confirm the test environment is ready — no new files or dependencies
needed for this feature.

- [X] T001 Verify `cd src && uv run pytest` passes before starting any changes

---

## Phase 2: Foundational

*No foundational tasks — this feature modifies existing files only and introduces
no shared infrastructure. Proceed directly to user story phases.*

---

## Phase 3: User Story 1 — Team file path validation (Priority: P1) 🎯 MVP

**Goal**: `--team` pointing to a directory exits 1 with a specific, user-friendly
JSON error message identifying the path as a directory.

**Independent Test**: Run `uv run pytest tests/unit/test_validator.py tests/contract/test_cli_contract.py -v` — all US1 tests pass, no regressions.

### Tests for User Story 1

> Write these tests FIRST. T002 is expected RED until T003 is applied.
> T003 is expected RED until T004 is applied.

- [X] T002 [P] [US1] Add `test_team_path_is_directory` to `TestFileAccessErrors` in `tests/unit/test_validator.py` — assert `FileLoadError` is raised with `"directory"` in the message when `path = tmp_path` (an existing directory)
- [X] T003 [P] [US1] Add `test_team_directory_exits_one` to `TestExitCodes` in `tests/contract/test_cli_contract.py` — invoke CLI with `--team str(tmp_path)`, assert exit code 1, stdout parses as JSON, `data["success"] is False`, `"error"` is present

### Implementation for User Story 1

- [X] T004 [US1] Add `is_dir()` guard to `load_team_roster` in `src/buddy_scheduler/validator.py` after the `exists` check: `if path.is_dir(): raise FileLoadError(f"Team roster path is a directory, not a file: {path}")`

**Checkpoint**: Run `uv run pytest tests/unit/test_validator.py::TestFileAccessErrors::test_team_path_is_directory tests/contract/test_cli_contract.py::TestExitCodes::test_team_directory_exits_one -v` — both tests GREEN.

---

## Phase 4: User Story 2 — History file validation (Priority: P2)

**Goal**: `--history` pointing to a directory, a zero-byte file, a non-JSON file,
or a JSON file with the wrong schema all exit 1 with a structured JSON error.

**Independent Test**: Run `uv run pytest tests/unit/test_history.py tests/contract/test_cli_contract.py::TestHistoryFlags -v` — all US2 tests pass.

### Tests for User Story 2

> Write all unit tests (T005–T008) before the implementation tasks (T009–T010).
> T005 and T006 are expected RED until T009 and T010 are applied.
> T007 and T008 may already be GREEN (existing Pydantic/JSON validation).
> T011 and T012 (CLI tests) run against the same code paths.

- [X] T005 [P] [US2] Add `test_directory_path_raises_file_load_error` to `TestLoadHistory` in `tests/unit/test_history.py` — call `load_history(tmp_path)` (directory), assert `FileLoadError` with `"directory"` in message
- [X] T006 [P] [US2] Add `test_zero_byte_file_raises_file_load_error` to `TestLoadHistory` in `tests/unit/test_history.py` — write a zero-byte file, call `load_history(p)`, assert `FileLoadError` with `"empty"` in message
- [X] T007 [P] [US2] Add `test_json_array_root_raises_data_validation_error` to `TestLoadHistory` in `tests/unit/test_history.py` — write `[1, 2, 3]` as JSON, call `load_history(p)`, assert `DataValidationError`
- [X] T008 [P] [US2] Add `test_json_null_root_raises_error` to `TestLoadHistory` in `tests/unit/test_history.py` — write `null` as JSON, call `load_history(p)`, assert `FileLoadError` or `DataValidationError`
- [X] T011 [P] [US2] Add `test_history_directory_exits_one` to `TestHistoryFlags` in `tests/contract/test_cli_contract.py` — invoke CLI with valid team + `--history str(tmp_path)`, assert exit 1, JSON error body
- [X] T012 [P] [US2] Add `test_history_non_json_exits_one` to `TestHistoryFlags` in `tests/contract/test_cli_contract.py` — write a file with `"not json"`, invoke CLI with `--history` pointing to it, assert exit 1, JSON error body

### Implementation for User Story 2

- [X] T009 [US2] Add `is_dir()` guard to `load_history` in `src/buddy_scheduler/history.py` after the `exists` check: `if path.is_dir(): raise FileLoadError(f"History path is a directory, not a file: {path}")`
- [X] T010 [US2] Add empty-file guard to `load_history` in `src/buddy_scheduler/history.py` after `raw = path.read_text(...)`: `if not raw.strip(): raise FileLoadError(f"History file is empty: {path}")`

**Checkpoint**: Run `uv run pytest tests/unit/test_history.py tests/contract/test_cli_contract.py::TestHistoryFlags -v` — all US2 tests GREEN.

---

## Phase 5: User Story 3 — Numeric parameter boundary values (Priority: P2)

**Goal**: `--history-weight 0.0` and `--tz-weight 0.0` succeed (exit 0); non-numeric
strings exit non-zero. No production code changes needed — tests document existing
behaviour.

**Independent Test**: Run `uv run pytest tests/contract/test_cli_contract.py::TestExitCodes -v -k "weight"` — all four weight boundary tests GREEN.

### Tests for User Story 3

> All four tests below are expected GREEN on first run (existing behaviour).
> If any are RED, investigate before adding production code.

- [X] T013 [P] [US3] Add `test_history_weight_zero_exits_zero` to `TestExitCodes` in `tests/contract/test_cli_contract.py` — invoke CLI with valid team + `--history-weight 0.0`, assert exit code 0 and `data["success"] is True`
- [X] T014 [P] [US3] Add `test_tz_weight_zero_exits_zero` to `TestExitCodes` in `tests/contract/test_cli_contract.py` — invoke CLI with valid team + `--tz-weight 0.0`, assert exit code 0 and `data["success"] is True`
- [X] T015 [P] [US3] Add `test_history_weight_non_numeric_exits_nonzero` to `TestExitCodes` in `tests/contract/test_cli_contract.py` — invoke CLI with valid team + `--history-weight high`, assert `result.exit_code != 0`
- [X] T016 [P] [US3] Add `test_tz_weight_non_numeric_exits_nonzero` to `TestExitCodes` in `tests/contract/test_cli_contract.py` — invoke CLI with valid team + `--tz-weight medium`, assert `result.exit_code != 0`

**Checkpoint**: Run `uv run pytest tests/contract/test_cli_contract.py -v` — all contract tests GREEN including the four new weight boundary tests.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T017 Run full default suite and confirm no regressions: `cd src && uv run pytest --cov=src/buddy_scheduler --cov-report=term-missing`
- [X] T018 [P] Run ruff: `cd src && uv run ruff check .` — zero violations
- [X] T019 [P] Run mypy: `cd src && uv run mypy src` — zero errors

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: N/A for this feature
- **US1 (Phase 3)**: No dependencies — start after T001
- **US2 (Phase 4)**: No dependencies on US1 — can start in parallel with US3
- **US3 (Phase 5)**: No dependencies on US1 or US2 — can start immediately after T001
- **Polish (Phase 6)**: Requires all story phases complete

### User Story Dependencies

- **US1 (P1)**: Independently testable — modifies `validator.py` and `test_cli_contract.py`
- **US2 (P2)**: Independently testable — modifies `history.py`, `test_history.py`, and `test_cli_contract.py`
- **US3 (P2)**: Independently testable — modifies only `test_cli_contract.py`; no production code changes

### Within Each User Story (TDD order)

1. Write all tests for the story
2. Run tests — observe RED/GREEN
3. Apply production code fix for each RED test
4. Re-run until all GREEN
5. Run full suite for regression check

### Parallel Opportunities

- T002 and T003 (US1 tests) can be written in parallel
- T005, T006, T007, T008, T011, T012 (US2 tests) can all be written in parallel
- T013, T014, T015, T016 (US3 tests) can all be written in parallel
- T009 and T010 (US2 production fixes) can be applied in parallel (different lines in history.py)
- US2 and US3 phases can run in parallel once US1 is complete (different files)
- T018 and T019 (ruff and mypy) can run in parallel

---

## Parallel Example: User Story 2

```bash
# Write all US2 unit tests together (different methods in same class — sequential edit):
tests/unit/test_history.py — add test_directory_path, test_zero_byte_file, test_json_array_root, test_json_null_root

# Write all US2 contract tests together:
tests/contract/test_cli_contract.py — add test_history_directory_exits_one, test_history_non_json_exits_one

# Apply both production code fixes:
src/buddy_scheduler/history.py — add is_dir() guard (line ~107)
src/buddy_scheduler/history.py — add empty-file guard (line ~112)
```

---

## Implementation Strategy

### MVP (User Story 1 only)

1. Complete T001 (verify baseline)
2. Complete T002–T003 (write US1 tests)
3. Complete T004 (add `is_dir` guard in validator.py)
4. **STOP and VALIDATE**: Run US1 tests — both GREEN
5. Directory-as-team-path is now explicitly handled with a clear message

### Full Delivery

1. MVP above (US1)
2. US2 (T005–T012) — history file validation
3. US3 (T013–T016) — weight boundary documentation
4. Polish (T017–T019) — full suite, ruff, mypy

---

## Notes

- All new tests belong in existing test files — no new test modules are created
- Total new production code: ~5 lines across 2 files
- Total new test cases: 12 across 3 existing test files
- Tests expected RED before fix: T002, T003 (US1) and T005, T006 (US2 empty/directory unit tests)
- Tests expected GREEN on first run: T007, T008, T011, T012, T013, T014, T015, T016
- Commit after each story phase is complete and all tests are GREEN
