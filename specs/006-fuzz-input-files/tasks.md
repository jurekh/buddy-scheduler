# Tasks: Fuzz Testing for Team Roster and History Files

**Input**: Design documents from `/specs/006-fuzz-input-files/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**TDD note**: The fuzz tests for binary content (T007, T009) will be initially RED because
`path.read_text(encoding="utf-8")` raises `UnicodeDecodeError` (not a subclass of `OSError`)
when the file contains non-UTF-8 bytes, and neither loader currently catches it. The RED
tests drive production code fixes T008 and T010. All other fuzz tests are expected GREEN on
first run (the loaders' YAML/JSON parsing already raises typed domain exceptions).

**Organization**: Tasks are grouped by user story. US1 and US2 are both P1 and can be
worked sequentially (they share the same file). US3 (P2) depends on US1+US2 fixes being
in place since the CLI delegates to the same loaders.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story this task belongs to

---

## Phase 1: Setup

**Purpose**: Install the new dev dependency, create the test module directory, verify the
baseline test suite still passes before adding any new code.

- [X] T001 Verify `uv run pytest` passes before starting (baseline check — expect 154+ tests GREEN)
- [X] T002 [P] Add `hypothesis>=6.0` to `[dependency-groups].dev` in `pyproject.toml`
- [X] T003 [P] Create `tests/fuzz/__init__.py` (empty file — makes `tests/fuzz/` a package)
- [X] T004 Run `uv lock` to regenerate `uv.lock` with hypothesis included (depends on T002)

**Checkpoint**: `uv run python -c "import hypothesis; print(hypothesis.__version__)"` succeeds.

---

## Phase 2: Foundational

**Purpose**: Create the test module skeleton that all user story tasks extend. Must be
complete before any user story tests can be written (they all append to the same file).

- [X] T005 Create `tests/fuzz/test_fuzz_loaders.py` with:
  - Module docstring explaining the safety contract being tested
  - All imports: `from __future__ import annotations`, `json`, `datetime.timedelta`,
    `pathlib.Path`, `pytest`, `yaml`, `hypothesis` (`given`, `settings`, `HealthCheck`),
    `hypothesis.strategies as st`, `buddy_scheduler.cli.main`,
    `buddy_scheduler.history.load_history`, `buddy_scheduler.models.*`,
    `buddy_scheduler.validator.load_team_roster`, `click.testing.CliRunner`
  - `_SLOW_SETTINGS = settings(max_examples=100, deadline=timedelta(seconds=5), database=None, suppress_health_check=[HealthCheck.function_scoped_fixture])`
  - `_ROSTER_CORPUS`: `st.one_of(st.binary(), st.text(), st.just(""), st.just("null"), st.just("{}"), st.just("!!python/object/apply:os.system ['id']"), st.just("!!python/object/new:subprocess.Popen [['id']]"), st.just("!!python/tuple [1, 2, 3]"), st.just("!!python/name:os.getcwd"), st.text(min_size=10_001, max_size=12_000), st.binary(min_size=1_048_576, max_size=1_100_000), st.lists(st.fixed_dictionaries({"name": st.text(min_size=0, max_size=64), "timezone": st.text(min_size=0, max_size=32), "active": st.booleans(), "avoid_buddies": st.lists(st.text(min_size=1, max_size=20), max_size=5)}), min_size=0, max_size=10).map(yaml.safe_dump))`
  - `_HISTORY_CORPUS`: `st.one_of(st.binary(), st.text(), st.just(""), st.just("null"), st.just("[]"), st.just("{}"), st.text(min_size=10_001, max_size=12_000), st.binary(min_size=1_048_576, max_size=1_100_000), st.recursive(st.none() | st.booleans() | st.integers() | st.text(), extend=lambda xs: st.lists(xs, max_size=3) | st.dictionaries(st.text(), xs, max_size=3), max_leaves=500).map(json.dumps), st.fixed_dictionaries({"pair_counts": st.dictionaries(st.text(min_size=1), st.dictionaries(st.text(min_size=1), st.integers())), "sit_out_counts": st.dictionaries(st.text(min_size=1), st.integers())}).map(json.dumps))`
  - `_valid_team()` helper: returns a `Path` written to `tmp_path / "team.yaml"` with a 4-member valid YAML roster (reused from the contract test pattern for US3)

  **Note**: `_valid_team()` in the fuzz context must write a fixed team file to a static
  temp location. For the fuzz test class, store the team path as a module-level fixture
  created in each test method using `tmp_path`.

**Checkpoint**: `uv run python -c "from tests.fuzz import test_fuzz_loaders"` imports without error.

---

## Phase 3: User Story 1 — Team roster parser safety contract (Priority: P1) 🎯

**Goal**: Prove that `load_team_roster` never raises an unhandled exception for any file
content. Fix the `UnicodeDecodeError` gap discovered by the binary-content fuzz test.

**Independent Test**: `uv run pytest tests/fuzz/test_fuzz_loaders.py::TestYamlSafeLoadEnforcement tests/fuzz/test_fuzz_loaders.py::TestFuzzTeamRoster -m slow --hypothesis-seed=42 -v` — all tests GREEN.

### Tests for User Story 1

> Write T006 and T007 FIRST. T007's `test_arbitrary_bytes_safety_contract` is expected
> RED until T008 is applied. T006 and `test_structured_yaml_safety_contract` are expected
> GREEN immediately.

- [X] T006 [US1] Add `TestYamlSafeLoadEnforcement` class to `tests/fuzz/test_fuzz_loaders.py`:
  - Class-level `@pytest.mark.parametrize("tag_content", [...])` with these 4 inputs:
    `"!!python/object/apply:os.system ['id']"`, `"!!python/object/new:subprocess.Popen [['id']]"`,
    `"!!python/tuple [1, 2, 3]"`, `"!!python/name:os.getcwd"`
  - Single test method `test_python_tag_is_rejected(self, tmp_path, tag_content)`:
    write `tag_content` to `tmp_path / "team.yaml"`, assert `pytest.raises(FileLoadError)` when
    calling `load_team_roster(path)`
  - No `@pytest.mark.slow` marker — these are fast, security-critical, always-on tests (FR-006)

- [X] T007 [US1] Add `TestFuzzTeamRoster` class to `tests/fuzz/test_fuzz_loaders.py`:
  - Decorate class with `@pytest.mark.slow`
  - Method 1: `test_arbitrary_bytes_safety_contract(self, tmp_path, content)`:
    `@given(content=st.binary())`, `@_SLOW_SETTINGS`; write `content` as bytes to
    `tmp_path / "team.yaml"`; safety assertion: try `load_team_roster(path)` → assert result
    is `list[TeamMember]`; except `(FileLoadError, DataValidationError)` → pass;
    except any other `Exception as exc` → `pytest.fail(f"Unexpected {type(exc).__name__}: {exc}")`
    **Expected RED** until T008 — `st.binary()` will generate non-UTF-8 bytes causing
    `UnicodeDecodeError` to escape the `except OSError` guard in `validator.py`
  - Method 2: `test_structured_yaml_safety_contract(self, tmp_path, content)`:
    `@given(content=_ROSTER_CORPUS)`, `@_SLOW_SETTINGS`; if `content` is `bytes` write
    with `write_bytes`, else `write_text(content, encoding="utf-8", errors="replace")`;
    same safety assertion pattern
    **Expected GREEN** on first run (YAML and string inputs either parse successfully or
    raise typed exceptions)

### Implementation for User Story 1

- [X] T008 [US1] Fix `UnicodeDecodeError` gap in `src/buddy_scheduler/validator.py`:
  Change the `read_text` try/except block from `except OSError` to
  `except (OSError, UnicodeDecodeError)` and raise
  `FileLoadError(f"Team roster file contains invalid UTF-8: {path}")` for the
  `UnicodeDecodeError` branch. Re-run T007's `test_arbitrary_bytes_safety_contract`
  to confirm GREEN.

**Checkpoint**: `uv run pytest tests/fuzz/test_fuzz_loaders.py::TestYamlSafeLoadEnforcement tests/fuzz/test_fuzz_loaders.py::TestFuzzTeamRoster -m slow --hypothesis-seed=42 -v` — all 6 tests (4 parametrized + 2 fuzz) GREEN.

---

## Phase 4: User Story 2 — History store parser safety contract (Priority: P1)

**Goal**: Prove that `load_history` never raises an unhandled exception for any file
content. Fix the same `UnicodeDecodeError` gap in the history loader.

**Independent Test**: `uv run pytest tests/fuzz/test_fuzz_loaders.py::TestFuzzHistory -m slow --hypothesis-seed=42 -v` — all tests GREEN.

### Tests for User Story 2

> Write T009 FIRST. `test_arbitrary_bytes_safety_contract` is expected RED until T010.
> `test_structured_json_safety_contract` is expected GREEN immediately.

- [X] T009 [US2] Add `TestFuzzHistory` class to `tests/fuzz/test_fuzz_loaders.py`:
  - Decorate class with `@pytest.mark.slow`
  - Method 1: `test_arbitrary_bytes_safety_contract(self, tmp_path, content)`:
    `@given(content=st.binary())`, `@_SLOW_SETTINGS`; write `content` as bytes to
    `tmp_path / "history.json"`; safety assertion: try `load_history(path)` → assert result
    is `PairingHistory`; except `(FileLoadError, DataValidationError)` → pass;
    except any other `Exception as exc` → `pytest.fail(f"Unexpected {type(exc).__name__}: {exc}")`
    **Expected RED** until T010 — same `UnicodeDecodeError` gap in `history.py`
  - Method 2: `test_structured_json_safety_contract(self, tmp_path, content)`:
    `@given(content=_HISTORY_CORPUS)`, `@_SLOW_SETTINGS`; if `content` is `bytes` write
    with `write_bytes`, else `write_text(content, encoding="utf-8", errors="replace")`;
    same safety assertion pattern
    **Expected GREEN** on first run

### Implementation for User Story 2

- [X] T010 [US2] Fix `UnicodeDecodeError` gap in `src/buddy_scheduler/history.py`:
  Change the `read_text` try/except block from `except OSError` to
  `except (OSError, UnicodeDecodeError)` and raise
  `FileLoadError(f"History file contains invalid UTF-8: {path}")` for the
  `UnicodeDecodeError` branch. Re-run T009's `test_arbitrary_bytes_safety_contract`
  to confirm GREEN.

**Checkpoint**: `uv run pytest tests/fuzz/test_fuzz_loaders.py::TestFuzzHistory -m slow --hypothesis-seed=42 -v` — all 2 tests GREEN.

---

## Phase 5: User Story 3 — CLI exit-code contract (Priority: P2)

**Goal**: Prove the CLI always exits with code 0 or 1 and always produces a valid JSON
error body on non-zero exit, regardless of what content is in `--team` or `--history`.

**Independent Test**: `uv run pytest tests/fuzz/test_fuzz_loaders.py::TestFuzzCLI -m slow --hypothesis-seed=42 -v` — both tests GREEN.

### Tests for User Story 3

> US3 depends on T008 and T010 being complete so that the loaders correctly convert
> UnicodeDecodeError to FileLoadError before reaching the CLI layer.

- [X] T011 [US3] Add `TestFuzzCLI` class to `tests/fuzz/test_fuzz_loaders.py`:
  - Decorate class with `@pytest.mark.slow`
  - `_CLI_SETTINGS = settings(max_examples=50, deadline=timedelta(seconds=10), database=None, suppress_health_check=[HealthCheck.function_scoped_fixture])` (10s deadline for CLI invocations; 50 examples to bound total CLI time)
  - Method 1: `test_team_file_content_exits_zero_or_one(self, tmp_path, content)`:
    `@given(content=st.binary())`, `@_CLI_SETTINGS`;
    write `content` as bytes to `tmp_path / "fuzz_team.yaml"`;
    `runner = CliRunner(); result = runner.invoke(main, ["--team", str(path)])`;
    `assert result.exit_code in (0, 1), f"exit_code={result.exit_code}: {result.output!r}"`;
    if `result.exit_code != 0`: `data = json.loads(result.stdout)`;
    `assert data["success"] is False`; `assert "error" in data`
    **Expected GREEN** — the CLI catches `BuddySchedulerError` subclasses (now including
    UnicodeDecodeError-wrapped-as-FileLoadError) and exits 1 with a JSON body
  - Method 2: `test_history_file_content_exits_zero_or_one(self, tmp_path, content)`:
    `@given(content=st.binary())`, `@_CLI_SETTINGS`;
    write a fixed valid 4-member team YAML to `tmp_path / "team.yaml"`;
    write `content` as bytes to `tmp_path / "fuzz_history.json"`;
    `result = runner.invoke(main, ["--team", str(team_path), "--history", str(history_path)])`;
    same exit-code + JSON-error assertions as Method 1
    **Expected GREEN**

**Checkpoint**: `uv run pytest tests/fuzz/test_fuzz_loaders.py::TestFuzzCLI -m slow --hypothesis-seed=42 -v` — both tests GREEN.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T012 Run full default suite with coverage: `uv run pytest --cov=buddy_scheduler --cov-report=term-missing` — verify no regressions and coverage ≥ 80% (FR-009)
- [X] T013 [P] Run `uv run ruff check .` — zero violations
- [X] T014 [P] Run `uv run mypy src` — zero errors

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (hypothesis installed, `__init__.py` created)
- **US1 (Phase 3)**: Depends on Foundational (module skeleton in place)
- **US2 (Phase 4)**: Depends on US1 tests written (both append to same file); T010 is independent of T008
- **US3 (Phase 5)**: Depends on T008 and T010 both complete (CLI delegates to the fixed loaders)
- **Polish (Phase 6)**: Requires all story phases complete

### User Story Dependencies

- **US1 (P1)**: Tests (T006, T007) before production fix (T008) — TDD order
- **US2 (P1)**: Tests (T009) before production fix (T010) — TDD order; independent of US1 except for shared file
- **US3 (P2)**: Depends on T008 + T010 being complete

### Within Each User Story

1. Write tests first (observe RED where noted)
2. Apply production code fix for RED tests
3. Re-run until all GREEN
4. Move to next story

### Parallel Opportunities

- T002 (edit pyproject.toml) and T003 (create __init__.py) run in parallel — different files
- T013 (ruff) and T014 (mypy) run in parallel — independent checks
- US1 and US2 test writing (T006/T007 and T009) cannot fully run in parallel — same file;
  write sequentially or split the file into segments

---

## Parallel Example: User Story 1

```bash
# T006 and T007 append to the same file — write sequentially:
# 1. Add TestYamlSafeLoadEnforcement (T006)
# 2. Add TestFuzzTeamRoster (T007)

# Run the deterministic tests (no slow marker) immediately after T006:
uv run pytest tests/fuzz/test_fuzz_loaders.py::TestYamlSafeLoadEnforcement -v

# Run fuzz tests after T007 (expect RED for test_arbitrary_bytes):
uv run pytest tests/fuzz/test_fuzz_loaders.py::TestFuzzTeamRoster -m slow --hypothesis-seed=42 -v

# Apply fix (T008), then re-run:
uv run pytest tests/fuzz/test_fuzz_loaders.py::TestFuzzTeamRoster -m slow --hypothesis-seed=42 -v
```

---

## Implementation Strategy

### MVP (User Story 1 only)

1. Complete Phase 1 (T001–T004)
2. Complete Phase 2 (T005)
3. Write T006 (deterministic YAML tag test — GREEN immediately)
4. Write T007 (fuzz test — observe RED for binary content)
5. Apply T008 (fix UnicodeDecodeError in validator.py)
6. **STOP and VALIDATE**: `uv run pytest tests/fuzz/ -m slow --hypothesis-seed=42 -v` — all GREEN
7. The safety contract for the team roster loader is now verified

### Full Delivery

1. MVP above (US1)
2. US2 (T009–T010) — history loader safety contract
3. US3 (T011) — CLI exit-code contract
4. Polish (T012–T014) — ruff, mypy, coverage

---

## Notes

- All fuzz tests require `@pytest.mark.slow` to exclude from the default `pytest` run
- `TestYamlSafeLoadEnforcement` has NO `@pytest.mark.slow` — it runs in every default test suite invocation
- `database=None` in `@settings` makes runs purely seed-driven; reproduce any failure with `--hypothesis-seed=<N>`
- The `UnicodeDecodeError` fix is small (1 line each in `validator.py` and `history.py`) but critical — without it, the binary fuzz tests will always fail
- Total new production code: ~2 lines across 2 files (`except (OSError, UnicodeDecodeError)` in each loader)
- Total new test code: 1 new test module with 5 test classes and ~10 test methods
- Commit after each story phase is complete and all relevant tests are GREEN
- Run `uv lock` and commit `uv.lock` in the same commit as the `pyproject.toml` change (T002 + T004)
