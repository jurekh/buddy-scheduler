# Tasks: User Documentation (Diataxis)

**Input**: Design documents from `specs/002-diataxis-docs/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared state)
- **[Story]**: User story this task belongs to (US1–US7)
- All paths are relative to the repository root

---

## Phase 1: Setup

**Purpose**: Create the documentation and fixture directory skeletons before any content is written.

- [ ] T001 Create `docs/` directory tree: `docs/tutorial/`, `docs/how-to/`, `docs/reference/`, `docs/explanation/`
- [ ] T002 Create `tests/fixtures/` directory

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Validator fix and YAML fixtures. All user story test files depend on these.

**⚠️ CRITICAL**: No user story work can begin until T003 and T005–T009 are complete (doc tests invoke the validator; fixtures are required inputs).

- [ ] T003 Extend `src/buddy_scheduler/validator.py` — add second-pass `avoid_buddies` cross-reference: after parsing all members, raise `DataValidationError` for any `avoid_buddies` entry that does not match a known roster name (error message format: `"Member '{name}' has unrecognised avoid_buddies entry '{entry}' — no member named '{entry}' exists in the roster"`)
- [ ] T004 [P] Add unit tests for the validator fix in `tests/unit/test_validator.py`: `test_avoid_buddies_valid_reference` (no error), `test_avoid_buddies_unknown_name` (DataValidationError with member name and bad entry in message), `test_avoid_buddies_inactive_member_valid` (inactive member is still in roster — no error), `test_avoid_buddies_self_reference_ignored` (self-reference is not an error)
- [ ] T005 [P] Create `tests/fixtures/minimal.yaml` — 4 members (Alice/Bob/UTC+0, Charlie/Diana/America/New_York), no optional fields; content must match quickstart.md verbatim
- [ ] T006 [P] Create `tests/fixtures/full-example.yaml` — 6 members demonstrating all 4 fields: name, timezone, active (Frank inactive), avoid_buddies (Bob avoids Charlie); content must match quickstart.md verbatim
- [ ] T007 [P] Create `tests/fixtures/with-absence.yaml` — 4 members, Charlie has `active: false`; content must match quickstart.md verbatim
- [ ] T008 [P] Create `tests/fixtures/with-avoidance.yaml` — 4 members, Bob has `avoid_buddies: [Alice]`; content must match quickstart.md verbatim
- [ ] T009 [P] Create `tests/fixtures/unknown-avoid-buddy.yaml` — Alice has `avoid_buddies: [Alic]` (misspelled, non-existent); content must match quickstart.md verbatim

**Checkpoint**: Validator fix and all fixtures ready. User story implementation can now proceed in parallel.

---

## Phase 3: User Story 1 — Getting Started Tutorial (Priority: P1) 🎯 MVP

**Goal**: A new user with no prior knowledge follows the tutorial and generates their first valid pairing output.

**Independent Test**: Follow `docs/tutorial/getting-started.md` start to finish; generate pairing output without consulting any other documentation.

- [ ] T010 [P] [US1] Write `docs/tutorial/getting-started.md` — linear walkthrough: (1) prerequisites (Python 3.11+, uv), (2) install via `uv tool install buddy-scheduler`, (3) install alternative via snap (`sudo snap install buddy-scheduler --classic`), (4) create team roster — show `tests/fixtures/minimal.yaml` content verbatim, (5) run dry run `buddy-scheduler --team team.yaml`, (6) read the output — explain all 7 fields: `success`, `pairs`, `sitting_out`, `optimization_score`, `solve_time`, `solver_profile`, `history_updated`. No reference tables, no conceptual digressions.
- [ ] T011 [P] [US1] Write `tests/integration/test_docs_tutorial.py` — `test_tutorial_dry_run`: invoke `main` with `["--team", str(FIXTURES / "minimal.yaml")]`, assert `exit_code == 0`, parse stdout JSON, assert all 7 required fields present (`success`, `pairs`, `sitting_out`, `optimization_score`, `solve_time`, `solver_profile`, `history_updated`), assert `success is True` and `history_updated is False`. Use `CliRunner()` (no `mix_stderr`).

**Checkpoint**: Tutorial complete and its example test passes. MVP deliverable satisfied.

---

## Phase 4: User Story 2 — Track History Across Rounds (Priority: P2)

**Goal**: A coordinator runs two consecutive rounds and confirms the second round avoids repeating pairs from the first.

**Independent Test**: Follow `docs/how-to/track-history.md`; run two consecutive rounds with confirmed different pairings; use `--prune-history` to remove a departed member.

- [ ] T012 [P] [US2] Write `docs/how-to/track-history.md` — goal, prerequisites (tutorial completed), numbered steps: (1) run with `--update-history` (show auto-inferred path `team.history.json`), (2) confirm history file created, (3) run again and note different pairings, (4) remove departed member with `--prune-history`. Explain that `--prune-history` without `--update-history` has no effect and emits a warning. No tutorial steps, no algorithm explanation.
- [ ] T013 [P] [US2] Write `tests/integration/test_docs_how_to_history.py` — (a) `test_how_to_history_update`: invoke with `["--team", str(FIXTURES/"minimal.yaml"), "--update-history"]` in a `CliRunner` isolated filesystem (`runner.isolated_filesystem()`); assert `exit_code == 0`; assert all 7 required fields present in stdout JSON; assert `history_updated is True`. (b) `test_how_to_history_prune_without_update_warns`: invoke with `["--team", str(FIXTURES/"minimal.yaml"), "--prune-history"]`; assert `exit_code == 0`; assert `history_updated is False` (no warning assertion — `basicConfig` is a no-op after first call in test process).

**Checkpoint**: Track-history how-to and its tests pass independently.

---

## Phase 5: User Story 3 — Manage Absent Team Members (Priority: P2)

**Goal**: A coordinator can mark a member inactive, confirm they are excluded, then reactivate them.

**Independent Test**: Follow `docs/how-to/manage-absences.md`; set `active: false`, confirm member absent from pairs; restore `active: true`, confirm member in next pairing.

- [ ] T014 [P] [US3] Write `docs/how-to/manage-absences.md` — goal, prerequisites, numbered steps: (1) open team.yaml, (2) set `active: false` for the absent member, (3) run `buddy-scheduler --team team.yaml` and confirm the member is in `inactive_members` and absent from `pairs`, (4) restore `active: true` and confirm re-inclusion. Show `tests/fixtures/with-absence.yaml` content inline. No tutorial steps.
- [ ] T015 [P] [US3] Write `tests/integration/test_docs_how_to_absences.py` — (a) `test_how_to_absence_member_excluded`: invoke with `with-absence.yaml`; assert `exit_code == 0`; assert `success is True`; assert `"Charlie"` does not appear in any pair in `data["pairs"]`; assert `"Charlie"` in `data.get("inactive_members", [])`. (b) `test_how_to_absence_reactivated_member_included`: invoke with `minimal.yaml` (all active); assert `exit_code == 0`; assert `data["pairs"]` has length 2 (all 4 members paired).

**Checkpoint**: Manage-absences how-to and its tests pass independently.

---

## Phase 6: User Story 4 — Prevent Specific Pairings (Priority: P2)

**Goal**: A coordinator adds an `avoid_buddies` constraint; the constrained pair never appears; unrecognised names produce an actionable error.

**Independent Test**: Follow `docs/how-to/avoid-pairings.md`; configure avoidance for one pair; confirm pair never appears; test unrecognised-name error.

Depends on T003 (validator fix must be in place for the error-path test to work).

- [ ] T016 [P] [US4] Write `docs/how-to/avoid-pairings.md` — goal, prerequisites, numbered steps: (1) add `avoid_buddies` to a member entry (use manager/direct-report as the example), (2) show `tests/fixtures/with-avoidance.yaml` content inline, (3) run `buddy-scheduler --team team.yaml` and confirm the avoided pair is absent, (4) explain what happens when avoidance makes a valid pairing impossible (exit code 1, error field in output), (5) explain the unrecognised-name validation error (show `tests/fixtures/unknown-avoid-buddy.yaml` content inline, show the error message format, explain how to fix it).
- [ ] T017 [P] [US4] Write `tests/integration/test_docs_how_to_avoidance.py` — (a) `test_how_to_avoidance_pair_never_appears`: invoke with `with-avoidance.yaml`; assert `exit_code == 0`; assert neither `["Alice", "Bob"]` nor `["Bob", "Alice"]` appears in `data["pairs"]`. (b) `test_how_to_avoidance_unknown_name_errors`: invoke with `unknown-avoid-buddy.yaml`; assert `exit_code == 1`; parse stdout JSON; assert `data["success"] is False`; assert `"error"` in `data`; assert `"Alic"` in `data["error"]`.

**Checkpoint**: Avoid-pairings how-to and its tests pass independently.

---

## Phase 7: User Story 6 — CLI Reference (Priority: P3)

**Goal**: A user can look up any CLI option, team.yaml field, or output field with full detail from a single reference page.

**Independent Test**: For any CLI option, the reference answers: what it does, default, valid values/ranges, and any option interactions — without consulting other documentation.

- [ ] T018 [P] [US6] Write `docs/reference/cli.md` — structured reference (no narrative prose): table of all 8 options (`--team`, `--history`, `--update-history`, `--prune-history`, `--history-weight`, `--tz-weight`, `--solver-profile`, `--log-level`) with columns: option, type, required, default, valid values, description, interactions. Expand `--solver-profile` to include all 4 profiles and adaptive thresholds (N≤15→optimal, 16–60→balanced, N>60→fast). Expand `--prune-history` to state it requires `--update-history` and emits a WARNING without it. Expand `--history` to document auto-inferred path. Include 2–3 invocation examples per option group.
- [ ] T019 [P] [US6] Write `docs/reference/team-yaml.md` — structured reference: table of all 4 fields (`name`, `timezone`, `active`, `avoid_buddies`) with columns: field, type, required, default, constraints, description. Constraints: `name` must be unique and non-empty string; `timezone` must be a non-empty string; `active` must be a boolean; `avoid_buddies` must be a list of names that exist in the roster. Show `tests/fixtures/full-example.yaml` content inline as the complete worked example.
- [ ] T020 [P] [US6] Write `docs/reference/output-format.md` — structured reference: (1) success response table covering all always-present fields (`success`, `pairs`, `sitting_out`, `optimization_score`, `solve_time`, `solver_profile`, `history_updated`) and conditional fields (`solver_gap`, `peak_memory_mb`, `memory_delta_mb`, `inactive_members`, `avoidance_conflicts`); (2) failure response: `success: false` + `error` string; (3) exit codes table: code 0 (success), code 1 (validation error or infeasibility), code 2 (solver failure). Show one success and one failure example JSON block.
- [ ] T021 [US6] Write `tests/integration/test_docs_ref_cli.py` — four test functions: `test_ref_cli_negative_history_weight_errors` (invoke with `["--team", "...", "--history-weight", "-1.0"]`; assert `exit_code == 1`; assert `"error"` in parsed output), `test_ref_cli_negative_tz_weight_errors` (same pattern for `--tz-weight -1.0`), `test_ref_cli_invalid_solver_profile_errors` (invoke with `--solver-profile bogus`; assert `exit_code == 1`), `test_ref_cli_invalid_log_level_errors` (invoke with `--log-level VERBOSE`; assert `exit_code == 1`). All use `minimal.yaml` fixture.
- [ ] T022 [P] [US6] Write `tests/integration/test_docs_ref_output.py` — three test functions: `test_ref_output_success_fields_present` (invoke with `minimal.yaml`; assert all 7 always-present fields in stdout JSON), `test_ref_output_failure_fields_present` (invoke with a non-existent team file path; assert `exit_code == 1`; parse stdout; assert `success is False` and `"error"` in data), `test_ref_output_exit_codes` (exit 0: `minimal.yaml` success; exit 1: missing file; exit 2: not directly testable via unit — document with a comment).

**Checkpoint**: All three reference pages and their tests pass independently.

---

## Phase 8: User Story 5 — Documentation Regression Test Verification (Priority: P2)

**Goal**: Confirm the test suite catches breaking changes to the tool without manual documentation review.

**Independent Test**: Introduce a deliberate breaking change (e.g., rename `--team` to `--roster`); run `pytest`; at least one test fails with a message identifying the affected document.

- [ ] T023 [US5] Run `cd src && pytest tests/integration/` and confirm all doc example test files (tutorial, how-to × 3, ref × 2) are auto-discovered and pass. Confirm each failing test function name encodes both the document category and the specific example (e.g., `test_tutorial_dry_run`, `test_how_to_avoidance_unknown_name_errors`). No code changes needed if tests pass — this is a verification checkpoint.

**Checkpoint**: Automated documentation regression testing is confirmed functional.

---

## Phase 9: User Story 7 — MIP Explanation (Priority: P4)

**Goal**: A reader understands why the tool produces particular pairings and can predict the effect of tuning weights.

**Independent Test**: After reading `docs/explanation/how-mip-works.md`, a user can answer: what does raising `--history-weight` do; why might timezone-mismatched members still be paired; what does "gap tolerance" mean.

No automated tests for this story — the explanation is narrative and conceptual, with no runnable examples.

- [ ] T024 [US7] Write `docs/explanation/how-mip-works.md` — conceptual narrative only, no step-by-step commands, no reference tables: (1) what problem the tool solves, (2) objective function — weighted penalty sum minimised over candidate pairings (narrative + symbolic formula; no numeric examples), (3) hard constraints — coverage (each active member in exactly one pair) and avoidance (never violated), (4) sit-out fairness — odd team size: member with lowest sit-out count in history is preferred, (5) timezone scoring — string similarity between timezone label text; identical labels score zero penalty; implication: inconsistent label formats degrade grouping quality, (6) solver profiles — gap tolerance and time limit tradeoff; the four profiles and adaptive selection; direct reader to `docs/reference/cli.md` for the threshold table.

**Checkpoint**: MIP explanation complete. All documentation deliverables satisfied.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final quality gates across all user stories.

- [ ] T025 Run `cd src && pytest --cov=buddy_scheduler --cov-report=term-missing` and confirm coverage remains ≥ 80%
- [ ] T026 [P] Run `ruff check .` from repository root; confirm no linting violations in any new or modified Python file
- [ ] T027 [P] Review all 8 documentation files: confirm Diataxis boundary compliance — no tutorial steps inside reference pages, no how-to instructions inside explanations, no conceptual narrative inside how-to guides (each sentence classifiable as exactly one Diataxis type)
- [ ] T028 [P] Verify all option names (`--team`, `--history`, `--update-history`, `--prune-history`, `--history-weight`, `--tz-weight`, `--solver-profile`, `--log-level`) and all field names (`name`, `timezone`, `active`, `avoid_buddies`) used in docs match `specs/001-buddy-scheduler/contracts/cli-schema.md` and `specs/001-buddy-scheduler/contracts/team-roster-schema.yaml` exactly

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    └── Phase 2 (Foundational) — T003 validator fix, T004 validator tests, T005–T009 fixtures
            ├── Phase 3 (US1 — Tutorial + test)         [can start after Phase 2]
            ├── Phase 4 (US2 — Track History + test)    [can start after Phase 2]
            ├── Phase 5 (US3 — Manage Absences + test)  [can start after Phase 2]
            ├── Phase 6 (US4 — Avoid Pairings + test)   [can start after Phase 2; T003 required]
            └── Phase 7 (US6 — Reference docs + tests)  [can start after Phase 2]
                        |
                        └── Phase 8 (US5 — Regression verification)  [after Phase 3–7]
Phase 9 (US7 — MIP explanation)  [independent — no code deps; can start any time after Phase 1]
Phase 10 (Polish)  [after all story phases complete]
```

### User Story Dependencies

- **US1 (P1)**: Unblocked after Phase 2 — no dependency on other stories
- **US2 (P2)**: Unblocked after Phase 2 — independent of US1 (though tutorial is a user prerequisite, not an implementation prerequisite)
- **US3 (P2)**: Unblocked after Phase 2 — independent
- **US4 (P2)**: Unblocked after Phase 2 (T003 validator fix already in Phase 2) — independent
- **US5 (P2)**: Satisfied by the test files produced in US1–US4 and US6; verification (T023) runs after those phases
- **US6 (P3)**: Unblocked after Phase 2 — independent of US1–US4
- **US7 (P4)**: Unblocked after Phase 1 (no code deps at all) — independent

### Within Each User Story

- Doc file and test file for the same story can be written in parallel [P] (different files, no mutual dependency)
- Within US6: three reference doc files can be written in parallel; two test files can be written in parallel

---

## Parallel Example: US6 (largest parallel opportunity)

```bash
# All five US6 tasks can launch simultaneously:
Task [P]: Write docs/reference/cli.md       (T018)
Task [P]: Write docs/reference/team-yaml.md (T019)
Task [P]: Write docs/reference/output-format.md (T020)
Task [P]: Write tests/integration/test_docs_ref_cli.py (T021 — note: not [P] with T022 due to shared assertion setup, but parallel with T018-T020)
Task [P]: Write tests/integration/test_docs_ref_output.py (T022)
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T009) — **CRITICAL blocker**
3. Complete Phase 3: US1 tutorial + test (T010–T011)
4. **STOP and VALIDATE**: Run `cd src && pytest tests/integration/test_docs_tutorial.py` — must pass
5. Demo: A new user can follow `docs/tutorial/getting-started.md` and generate pairings

### Incremental Delivery

1. Setup + Foundational → infrastructure ready
2. US1 → validate independently → getting-started tutorial delivers immediate value
3. US2, US3, US4 → work in parallel → three how-to guides complete
4. US6 → reference documentation complete (three pages + tests)
5. US5 verification → confirm regression safety net is in place
6. US7 → explanation complete
7. Polish → coverage gate, lint, Diataxis audit

### Parallel Team Strategy

With two implementers, after Phase 2:
- Implementer A: US1 (P1) → then US2 (P2) → then US6 (P3)
- Implementer B: US3 (P2) → then US4 (P2) → then US7 (P4)

---

## Notes

- `[P]` = different files, no shared mutable state — safe to parallelise
- `[Story]` label maps each task to its user story for traceability
- Fixture content in doc prose must match fixture files on disk verbatim (single source of truth)
- `CliRunner()` without `mix_stderr=False` — use `result.output` for JSON (captures stdout in test context)
- Do not assert exact field values (`solve_time`, `optimization_score`, pair order) — assert field presence only
- `--prune-history` warning cannot be asserted in pytest (logging.basicConfig is a no-op after first call); assert behavioural outcome instead
- Commit after each phase checkpoint to preserve testable increments
