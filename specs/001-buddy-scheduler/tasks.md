# Tasks: buddy-scheduler

**Input**: Design documents from `/specs/001-buddy-scheduler/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/, research.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and toolchain configuration

- [ ] T001 Initialize uv project: create `pyproject.toml` with name `buddy-scheduler`, `requires-python = ">=3.11"`, runtime deps (pulp≥2.7, click≥8.1, pyyaml≥6.0, psutil≥5.9, pydantic≥2.0, filelock≥3.12), dev deps in `[dependency-groups]` (pytest≥7.0, pytest-cov≥4.0, ruff≥0.5, mypy≥1.0), entry point `buddy-scheduler = "buddy_scheduler.cli:main"`, and tool sections for ruff (select E,F,W,I,B,UP,N,A,C4,RET,SIM; line-length 88; isort), pytest (testpaths=tests, markers=[slow, benchmark], addopts="-m 'not slow'"), mypy (strict=true, pulp.* ignore_missing_imports override), coverage (source=src/buddy_scheduler, fail_under=80)
- [ ] T002 Create directory skeleton: `src/buddy_scheduler/__init__.py`, `src/buddy_scheduler/solver/__init__.py`, `tests/__init__.py`, `tests/contract/__init__.py`, `tests/integration/__init__.py`, `tests/unit/__init__.py`
- [ ] T003 [P] Pin Python version: create `.python-version` with content `3.11`; run `uv sync --all-groups` to generate `uv.lock`; commit both files
- [ ] T004 [P] Create `Makefile` with targets: `install` (uv sync --all-groups), `test` (uv run pytest tests --cov=src/buddy_scheduler --cov-report=term-missing), `lint` (uv run ruff check src tests), `format` (uv run ruff format src tests), `typecheck` (uv run mypy src), `all` (install test lint typecheck), `build` (uv build), `clean` (remove .venv .mypy_cache .ruff_cache __pycache__ dist .pytest_cache htmlcov)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Exception hierarchy, core data models, YAML validator, solver profile
config — required by every user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Define exception hierarchy at the top of `src/buddy_scheduler/models.py`: `BuddySchedulerError(Exception)` base with `message:str`; subclasses `FileLoadError`, `FileSaveError`, `DataValidationError`, `OptimizationError`; each with a one-line docstring
- [ ] T006 [P] Define core dataclasses in `src/buddy_scheduler/models.py` (after T005): `@dataclass TeamMember(name:str, timezone:str, active:bool=True, avoid_buddies:list[str]=field(default_factory=list))`; `@dataclass OptimizationResult(success:bool, pairs:list[tuple[str,str]], sitting_out:str|None, optimization_score:float, solve_time:float, solver_profile:str, solver_gap:float|None=None, peak_memory_mb:float|None=None, memory_delta_mb:float|None=None, inactive_members:list[str]=field(default_factory=list), avoidance_conflicts:list[str]=field(default_factory=list), error:str|None=None, history_updated:bool=False)`; add `to_dict()` method that serializes to a JSON-compatible dict (omit None-valued optional fields, sort pairs lexicographically)
- [ ] T007 [P] Define `SolverProfile` enum and `ProfileConfig` dataclass in `src/buddy_scheduler/solver/profiles.py`: `SolverProfile(Enum)` with members FAST/BALANCED/OPTIMAL/ADAPTIVE; `@dataclass ProfileConfig(gap_tolerance:float, time_limit_s:int, cbc_options:list[str])`; function `get_profile_config(profile:SolverProfile, n_active:int) -> ProfileConfig` implementing adaptive thresholds (N≤15→OPTIMAL: gap=0.001 time=300 options=['-strategy 1','-depth 10000','-cuts all']; 16≤N≤60→BALANCED: gap=0.01 time=60; N>60→FAST: gap=0.20 time=10); ADAPTIVE delegates to thresholds; other profiles return fixed config
- [ ] T008 [P] Unit tests for models and exceptions in `tests/unit/test_models.py`: exception hierarchy is-a relationships; `TeamMember` default field values; `OptimizationResult.to_dict()` omits None fields, sorts pairs, includes all required keys; exception messages preserved
- [ ] T009 [P] Implement YAML roster loader and validator in `src/buddy_scheduler/validator.py`: `load_team_roster(path:Path) -> list[TeamMember]`; raise `FileLoadError` if file missing, unreadable, or empty; call `yaml.safe_load`; raise `FileLoadError` if not a list or YAML parse fails; raise `DataValidationError` for missing `name`/`timezone`, duplicate names, non-bool `active`, non-list `avoid_buddies`; construct and return `list[TeamMember]`; log INFO "Loaded N members from {path}" after success
- [ ] T010 [P] Unit tests for validator in `tests/unit/test_validator.py`: valid roster loads correctly; missing file → `FileLoadError`; empty YAML → `FileLoadError`; duplicate names → `DataValidationError`; missing `timezone` → `DataValidationError`; non-bool `active` → `DataValidationError`; zero active members is valid (validation passes, pairing phase handles the error)
- [ ] T011 Implement logging configuration helper `_configure_logging(level:str) -> None` in `src/buddy_scheduler/cli.py`: call `logging.basicConfig(stream=sys.stderr, level=getattr(logging, level.upper()), format="%(asctime)s [%(levelname)s] %(message)s")`; raise `DataValidationError` for an unrecognised level string

**Checkpoint**: Foundation ready — user story implementation can begin

---

## Phase 3: User Story 1 — Generate Team Pairings (Priority: P1) 🎯 MVP

**Goal**: `buddy-scheduler --team team.yaml` produces valid pairings for all active
members, emits a JSON result to stdout, and writes logs to stderr.

**Independent Test** (from spec):
```bash
buddy-scheduler --team team.yaml
# Verify: each active member in exactly one pair; N/2 pairs for even N;
#         (N-1)/2 pairs + one sit-out for odd N; exit code 0; valid JSON on stdout
```

- [ ] T012 [P] [US1] Unit tests for core MIP solver (no penalties) in `tests/unit/test_mip.py`: even-N team → N/2 pairs, all members assigned exactly once; odd-N team → (N-1)/2 pairs + one sit-out; zero active members → returns failure result; result pairs are tuples sorted lexicographically; solver_profile field set correctly; solve_time > 0
- [ ] T013 [P] [US1] Implement MIP solver core in `src/buddy_scheduler/solver/mip.py`: function `solve_pairing(members:list[TeamMember], history_weight:float, tz_weight:float, history:PairingHistory|None, avoidance_pairs:set[frozenset[str]], profile:SolverProfile) -> OptimizationResult`; filter inactive members; raise (return failure) if fewer than 2 active; build `LpProblem`; create binary vars `x[i,j]` for i<j where both active (avoidance exclusion added in T028); add coverage constraints; set objective to zero penalty sum for now; invoke `PULP_CBC_CMD(msg=0)` with profile options from `get_profile_config`; on `LpStatusOptimal` extract pairs and sit-out from variable values (>0.5 threshold); populate `OptimizationResult` with solved pairs, sitting_out, optimization_score, solve_time, solver_profile (resolved name, not "adaptive"), inactive_members list
- [ ] T014 [P] [US1] Add psutil memory tracking in `src/buddy_scheduler/solver/mip.py`: record `psutil.Process().memory_info().rss` before and after `prob.solve()`; compute `peak_memory_mb = rss_after / 1_048_576`; `memory_delta_mb = (rss_after - rss_before) / 1_048_576`; log INFO "Solved in {solve_time:.3f}s, peak memory {peak_memory_mb:.1f} MB" at end of solve
- [ ] T015 [US1] Implement CLI `main()` entry point in `src/buddy_scheduler/cli.py`: `@click.command()` with options `--team PATH` (required), `--solver-profile TEXT` (default "adaptive"), `--log-level TEXT` (default "INFO"), `--history-weight FLOAT` (default 1.0), `--tz-weight FLOAT` (default 1.0); call `_configure_logging`; load roster with `load_team_roster`; call `solve_pairing` (pass empty avoidance set, no history, US1 only needs basic structure); serialize result via `result.to_dict()`; `json.dumps(d, indent=2)` → `print` to stdout; on any `BuddySchedulerError` serialize `{"success":false,"error":str(e)}` to stdout; `sys.exit(1)` on failure; `sys.exit(0)` on success
- [ ] T016 [US1] Contract tests for CLI output in `tests/contract/test_cli_contract.py`: use Click `CliRunner`; invoke with valid team file → exit code 0, stdout is valid JSON with keys success/pairs/sitting_out/optimization_score/solve_time/solver_profile; invoke with missing `--team` → exit code non-zero; invoke with non-existent team file → exit code 1, stdout has `success:false`; verify all log lines go to stderr (captured separately); verify stdout contains no log lines

**Checkpoint**: `buddy-scheduler --team team.yaml` is fully functional. US1 independently testable.

---

## Phase 4: User Story 2 — History-Aware Pairing (Priority: P2)

**Goal**: The tool loads a JSON history store, weights pairings by repetition frequency,
and optionally persists updated pairings after a successful run.

**Independent Test** (from spec):
```bash
buddy-scheduler --team team.yaml --history h.json --update-history
buddy-scheduler --team team.yaml --history h.json --update-history
# Verify: second run pairs differ from first run wherever alternatives exist
```

- [ ] T017 [P] [US2] Define `PairingHistory` dataclass in `src/buddy_scheduler/models.py`: `@dataclass PairingHistory(matrix:dict[str,dict[str,int]] = field(default_factory=dict), sit_out_counts:dict[str,int] = field(default_factory=dict))`; methods `get_pair_count(a:str, b:str) -> int` (returns 0 if absent); `increment_pair(a:str, b:str) -> None` (updates both directions symmetrically); `increment_sit_out(name:str) -> None`; `prune(active_names:set[str]) -> None` (removes all keys not in active_names from matrix and sit_out_counts, and removes those names from inner dicts)
- [ ] T018 [P] [US2] Implement history store loader in `src/buddy_scheduler/history.py`: `load_history(path:Path) -> PairingHistory`; use Pydantic v2 `BaseModel` `_HistoryModel(pair_counts:dict[str,dict[str,int]], sit_out_counts:dict[str,int])` for JSON validation; raise `FileLoadError` if file missing or not valid JSON; raise `DataValidationError` if matrix is asymmetric (check all stored pairs) or any count is negative; convert `_HistoryModel` → `PairingHistory` (rename `pair_counts` key to `matrix`); log INFO "Loaded history for N members"; `empty_history() -> PairingHistory` returns `PairingHistory()` with empty dicts
- [ ] T019 [P] [US2] Implement atomic history writer in `src/buddy_scheduler/history.py`: `save_history(history:PairingHistory, path:Path) -> None`; acquire `FileLock(str(path) + ".lock", timeout=10)`; serialize PairingHistory to dict (use key `pair_counts` for `matrix`); write to `NamedTemporaryFile(mode='w', dir=path.parent, delete=False, suffix='.tmp')`; `json.dump`; `os.fsync(tmp.fileno())`; if `path.exists()`: `os.replace(path, str(path) + ".backup")`; `os.replace(tmp_path, path)`; raise `FileSaveError` on any `OSError`; log INFO "Saved history to {path}"
- [ ] T020 [P] [US2] Unit tests for history store in `tests/unit/test_history.py`: valid JSON loads correctly; non-existent path returns empty history; malformed JSON → `FileLoadError`; asymmetric matrix → `DataValidationError`; save then load round-trips correctly; atomic write: temp file cleaned up on success; `.backup` file created on overwrite; prune removes absent members from matrix and sit_out_counts; sit_out_counts and pair_count increment symmetrically
- [ ] T021 [US2] Add history penalty to MIP objective in `src/buddy_scheduler/solver/mip.py`: when `history is not None` and `history_weight > 0`, add `history_weight * history.get_pair_count(name_i, name_j)` per pair variable to the objective sum; add sit-out penalty `sit_out_counts.get(name_i, 0)` per sit-out variable multiplied by a fixed weight (1.0) so the least-sat-out member is preferred; extend `tests/unit/test_mip.py` with a test that verifies the less-frequently-paired member is selected when there is a clear winner
- [ ] T022 [US2] Update CLI with history flags in `src/buddy_scheduler/cli.py`: add `--history PATH` (optional), `--update-history` (flag, default False), `--prune-history` (flag, default False); if `--history` provided: call `load_history`; pass `PairingHistory` to `solve_pairing`; if `--update-history` and `result.success`: call `history.increment_pair` for each pair, `history.increment_sit_out` if sitting_out set; if `--prune-history`: call `history.prune(active_names)`; call `save_history`; set `result.history_updated=True`; if `--prune-history` without `--update-history`: log WARNING and ignore prune; add contract test in `tests/contract/test_cli_contract.py` for `--update-history` creating history file

**Checkpoint**: Two sequential runs with `--update-history` produce different pairings. US2 independently testable.

---

## Phase 5: User Story 3 — Timezone-Compatible Pairing (Priority: P2)

**Goal**: Pairings prefer members with similar timezone strings; the weight is
configurable at invocation time.

**Independent Test** (from spec):
```bash
buddy-scheduler --team two-tz-groups.yaml --tz-weight 2.0 --history-weight 0.0
# Verify: pairings predominantly match members within the same timezone group
```

- [ ] T023 [P] [US3] Implement timezone utility in `src/buddy_scheduler/tz_utils.py`: `tz_penalty(tz_a:str, tz_b:str) -> float`; compute `1.0 - difflib.SequenceMatcher(None, tz_a.strip(), tz_b.strip()).ratio()`; return `1.0` if either string is empty; no side effects; include module docstring
- [ ] T024 [P] [US3] Unit tests for timezone utility in `tests/unit/test_tz_utils.py`: identical strings → 0.0; completely different strings → 1.0; partial match returns value in (0, 1); empty string → 1.0; case-sensitive comparison verified; common timezone formats ("America/New_York", "UTC+1", "EMEA", "BST") behave reasonably
- [ ] T025 [US3] Add timezone penalty to MIP objective in `src/buddy_scheduler/solver/mip.py`: when `tz_weight > 0`, add `tz_weight * tz_penalty(tz_i, tz_j)` per pair variable to the objective; both history and timezone terms combine additively; extend `tests/unit/test_mip.py` with a test that uses high `tz_weight` and zero `history_weight` and verifies timezone-compatible pairs are preferred over cross-timezone pairs when a clear split exists

**Checkpoint**: `--tz-weight` controls timezone preference. US3 independently testable.

---

## Phase 6: User Story 4 — Avoidance Constraints and Inactive Members (Priority: P3)

**Goal**: Named avoidance pairs are never produced; infeasible constraint sets are
reported explicitly; solver failure triggers a fallback chain.

**Independent Test** (from spec):
```bash
buddy-scheduler --team avoidance-team.yaml   # avoidance pair + inactive member configured
# Run 10 times; verify avoidance pair never appears; inactive member never appears;
# exit code 0 with valid pairs
```

- [ ] T026 [P] [US4] Unit tests for avoidance and inactive in `tests/unit/test_mip.py`: avoidance pair (A,B) never appears in output across multiple seeds; inactive member never appears in any pair; infeasibility case (A avoids everyone) returns `success:false` with `avoidance_conflicts` set; fallback activation logged on forced solver timeout; round-robin, random, greedy results honour avoidance constraints
- [ ] T027 [P] [US4] Implement fallback strategies in `src/buddy_scheduler/solver/fallback.py`: three functions sharing signature `(members, history_weight, tz_weight, history, avoidance_pairs, profile_name) -> OptimizationResult`; `greedy_min_penalty`: build cost dict, iteratively select lowest-cost unpaired pair respecting avoidance; `random_pairing`: shuffle active members, pair sequentially respecting avoidance with retry; `round_robin_pairing`: deterministic rotation-based pairing respecting avoidance; all set `solver_profile = f"{profile_name}_fallback_{strategy_name}"`, `solver_gap=None`; all set `solve_time` and memory fields; unit tests in `tests/unit/test_fallback.py`
- [ ] T028 [US4] Add avoidance constraint logic in `src/buddy_scheduler/solver/mip.py`: at solve start compute `avoidance_pairs:set[frozenset[str]]` from all `TeamMember.avoid_buddies` lists (symmetric); exclude forbidden pairs from variable creation (no `x[i,j]` for avoidance pairs); after PuLP reports `LpStatusInfeasible`: compute `avoidance_conflicts` — for each active member find those with no eligible partners; return `OptimizationResult(success=False, avoidance_conflicts=[...], ...)` with string descriptions; exit code 1 (handled in CLI)
- [ ] T029 [US4] Add fallback chain in `src/buddy_scheduler/solver/mip.py`: when solve status is not `LpStatusOptimal` and not `LpStatusInfeasible`: log WARNING "MIP solver returned status {status}, attempting fallback: greedy"; try `greedy_min_penalty`; on failure log WARNING "greedy failed, attempting fallback: random"; try `random_pairing`; on failure log WARNING "random failed, attempting fallback: round_robin"; try `round_robin_pairing`; if all fail raise `OptimizationError("All fallback strategies exhausted")`; CLI catches `OptimizationError` and exits with code 2
- [ ] T030 [US4] Unit tests for fallback chain in `tests/unit/test_fallback.py`: greedy selects lowest-penalty eligible pair; random produces valid pairings on repeated calls; round-robin produces deterministic result; all strategies honour avoidance constraints; `solver_profile` encoding correct for each strategy; `OptimizationError` raised when all strategies fail (forced by full avoidance); exit code 2 test via CliRunner in `tests/contract/test_cli_contract.py`

**Checkpoint**: Avoidance constraints hard-enforced; infeasibility reported; fallbacks activate on solver failure. US4 independently testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Integration, performance validation, coverage check, sample data

- [ ] T031 [P] Integration tests in `tests/integration/test_pipeline.py`: full CLI invocation for even-N team; full CLI for odd-N team (sit-out correct); two sequential runs with `--update-history` produce different pairs where alternatives exist; `--prune-history` removes stale members from history file on disk; avoidance infeasibility → exit code 1, `avoidance_conflicts` in JSON; malformed YAML → exit code 1, valid JSON error; missing team file → exit code 1, valid JSON error; `--update-history` without `--history` → history auto-created at inferred path
- [ ] T032 [P] Performance test in `tests/unit/test_mip.py` (marked `@pytest.mark.slow`): build 100-member team with randomised timezones and random history; time `solve_pairing` call; assert wall-clock ≤ 5 seconds (SC-004)
- [ ] T033 [P] Create `examples/team.yaml` with 8 members: two timezone groups (UTC+0, America/New_York), one inactive member, one avoidance pair; usable as the manual validation target in `quickstart.md`
- [ ] T034 Run `make all` to verify: test suite passes, coverage ≥ 80%, ruff check clean, mypy strict clean; fix any issues found

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Requires T001–T002 complete — BLOCKS all user stories
- **User Stories (Phase 3–6)**: All require Phase 2 complete; can proceed in priority order or in parallel if staffed
- **Polish (Phase 7)**: Requires all desired user stories complete

### User Story Dependencies

- **US1 (Phase 3, P1)**: Requires Phase 2 — no dependency on US2/US3/US4
- **US2 (Phase 4, P2)**: Requires Phase 2 — integrates with US1 solver but independently testable
- **US3 (Phase 5, P2)**: Requires Phase 2 — adds to MIP objective; can be worked in parallel with US2
- **US4 (Phase 6, P3)**: Requires Phase 2 — modifies solver variable creation; most naturally after US1 complete

### Within Each User Story

- Tests (T012, T017–T020, T023–T024, T026–T027, T030) should be written and failing before implementation where feasible
- Models before services; services before CLI wiring
- Core solver changes (T013, T021, T025, T028) before fallback (T029)

### Parallel Opportunities

- T003 and T004 are parallel within Phase 1
- T006, T007, T008, T009, T010 are parallel within Phase 2 (all depend only on T005)
- T012, T013, T014 are parallel within Phase 3
- T017, T018, T019, T020 are parallel within Phase 4
- T023, T024 are parallel within Phase 5
- T026, T027 are parallel within Phase 6
- T031, T032, T033 are parallel within Phase 7
- US3 (Phase 5) can be worked in parallel with US2 (Phase 4) if staffed separately

---

## Parallel Example: User Story 1

```bash
# After Phase 2 completes, launch these together:
Task T012: "Unit tests for core MIP solver in tests/unit/test_mip.py"
Task T013: "Implement MIP solver core in src/buddy_scheduler/solver/mip.py"
Task T014: "Add psutil memory tracking in src/buddy_scheduler/solver/mip.py"

# After T013 and T014 complete:
Task T015: "Implement CLI main() in src/buddy_scheduler/cli.py"

# After T015:
Task T016: "Contract tests in tests/contract/test_cli_contract.py"
```

## Parallel Example: User Story 2

```bash
# After Phase 2 completes, launch these together:
Task T017: "PairingHistory dataclass in src/buddy_scheduler/models.py"
Task T018: "History store loader in src/buddy_scheduler/history.py"
Task T019: "Atomic history writer in src/buddy_scheduler/history.py"
Task T020: "Unit tests for history store in tests/unit/test_history.py"

# After T017:
Task T021: "Add history penalty to MIP objective"

# After T021:
Task T022: "Update CLI with history flags"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: `buddy-scheduler --team examples/team.yaml` produces valid JSON with correct pairs
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → basic pairing works → demo
3. US2 → history tracking works → demo
4. US3 → timezone weighting works → demo
5. US4 → avoidance constraints + fallbacks → demo
6. Polish → full suite + performance confirmed → release

### Parallel Team Strategy

With two developers after Phase 2:
- Developer A: US1 (Phase 3) → US4 (Phase 6)
- Developer B: US2 (Phase 4) → US3 (Phase 5) in parallel

---

## Notes

- [P] tasks = different files, no incomplete dependencies — can be launched simultaneously
- [Story] label maps each task to its user story for independent traceability
- Each user story is independently completable and testable
- Tests should fail before implementation; fix implementation until tests pass
- Commit after each task or logical group
- Stop at any phase checkpoint to validate the story independently
- `@pytest.mark.slow` gates performance and resource tests out of the default run
