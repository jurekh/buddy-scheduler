# Tasks: Snap Strict Confinement

**Input**: Design documents from `specs/003-snap-strict/`
**Prerequisites**: plan.md, spec.md, research.md, quickstart.md

**Organization**: Two user stories. US1 is the core change (snapcraft.yaml edit +
build verification). US2 is Snap Store review eligibility. Both depend on the
same foundational edit so they share Phase 2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup

**Purpose**: Confirm tooling is available before making changes.

- [x] T001 Verify snapcraft is installed and the current snap builds cleanly: run `snapcraft --use-lxd` from repo root and confirm it produces a `.snap` file

**Checkpoint**: Baseline snap build confirmed. Proceed to edit.

---

## Phase 2: Foundational — Update snap/snapcraft.yaml

**Purpose**: Apply all four research-driven changes to `snap/snapcraft.yaml`.
This single file edit is the prerequisite for both user stories.

**⚠️ CRITICAL**: Both user stories depend on this phase being complete.

- [x] T002 In `snap/snapcraft.yaml`: change `confinement: classic` to `confinement: strict`
- [x] T003 In `snap/snapcraft.yaml`: remove the entire `override-build:` block (the 6-line script that copies the Python binary — no longer needed under strict confinement per research Decision 1)
- [x] T004 In `snap/snapcraft.yaml`: remove `build-packages: [python3-dev]` from the part (the Python plugin adds it automatically; redundant per research Decision 4)
- [x] T005 In `snap/snapcraft.yaml`: replace the `environment:` block in `apps.buddy-scheduler` with `plugs: [home]` (the explicit PYTHONPATH/PATH were classic-only workarounds per research Decision 2; `home` grants $HOME access per research Decision 3)

**Checkpoint**: snapcraft.yaml updated. Both user stories can now proceed.

---

## Phase 3: User Story 1 — Install without --classic (Priority: P1) 🎯 MVP

**Goal**: Verify the snap installs and operates correctly under strict confinement
with no `--classic` flag.

**Independent Test**: Build the snap, sideload it with `--dangerous` only, run
`buddy-scheduler --team ~/team.yaml`, confirm valid JSON output and no permission
errors.

- [x] T006 [US1] Build the snap from the updated `snap/snapcraft.yaml`: run `snapcraft --use-lxd` and confirm it completes without errors and produces a `.snap` artifact
- [ ] T007 [US1] Sideload the built snap without `--classic`: run `sudo snap install --dangerous buddy-scheduler_*.snap` and confirm installation succeeds
- [ ] T008 [US1] Verify the `home` interface auto-connected: run `snap connections buddy-scheduler` and confirm `home` plug shows as connected (if not, run `sudo snap connect buddy-scheduler:home :home`)
- [ ] T009 [US1] Smoke test — file in `$HOME`: copy `tests/fixtures/minimal.yaml` to `~/team.yaml`, run `buddy-scheduler --team ~/team.yaml`, confirm exit 0 and `"success": true` in JSON output
- [ ] T010 [US1] Smoke test — history write in `$HOME`: run `buddy-scheduler --team ~/team.yaml --update-history`, confirm `~/team.history.json` is created and contains valid JSON
- [ ] T011 [US1] Smoke test — clear error on path blocked by confinement: run `sudo cp tests/fixtures/minimal.yaml /root/team.yaml && buddy-scheduler --team /root/team.yaml`, confirm exit 1 and a readable file-load error message (not a Python traceback). Note: `/tmp/` is permitted by the base AppArmor policy for all strict snaps and is not a valid test of confinement boundaries.
- [ ] T012 [US1] Verify snap confinement label: run `snap info buddy-scheduler | grep confinement`, confirm output is `confinement: strict`
- [ ] T013 [US1] Clean up smoke test artefacts: remove `~/team.yaml`, `~/team.history.json`, `/tmp/team.yaml`

**Checkpoint**: Snap installs without `--classic` and all file-access scenarios pass.

---

## Phase 4: User Story 2 — Snap Store Eligibility (Priority: P2)

**Goal**: Verify the snap package passes Snap Store review tooling without any
classic-confinement warning.

**Independent Test**: Run `snap review` (or `review-tools`) on the built `.snap`
file and confirm no classic-confinement violations are reported.

- [ ] T014 [US2] Install Snap Store review tools if not present: `sudo snap install review-tools`
- [ ] T015 [US2] Run review tools on the built snap: `review-tools.snap-review buddy-scheduler_*.snap`, confirm no `classic-confinement` errors or warnings in the output

**Checkpoint**: Snap is eligible for automated Snap Store review.

---

## Phase 5: Polish

**Purpose**: Update documentation to reflect that `--classic` is no longer required.

- [x] T016 [P] In `docs/tutorial/getting-started.md` Option D: replace `sudo snap install buddy-scheduler --classic` with `sudo snap install buddy-scheduler` and remove the paragraph explaining why `--classic` was required (it no longer is)
- [x] T017 [P] Run the existing test suite to confirm no regressions: `python -m pytest` from repo root, confirm all 140 tests pass
- [x] T018 Run `ruff check .` and confirm no new lint violations

**Checkpoint**: Docs updated, test suite green, lint clean.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS both user stories
- **US1 (Phase 3)**: Depends on Phase 2
- **US2 (Phase 4)**: Depends on Phase 2; can run in parallel with US1 after Phase 2 (uses the same built `.snap` artifact)
- **Polish (Phase 5)**: Depends on Phase 3 completing (confirms `--classic` is no longer needed)

### User Story Dependencies

- **US1 (P1)**: No dependency on US2 — independently testable
- **US2 (P2)**: No dependency on US1 — independently testable once snap is built

### Within Each User Story

- T006 (build) must complete before T007–T013 (install and smoke tests)
- Smoke tests T009–T011 can run in any order after T008

### Parallel Opportunities

- T016 (doc update), T017 (test suite), T018 (ruff) in Phase 5 can all run in parallel
- US1 (Phase 3) and US2 (Phase 4) can run in parallel after the snap is built (T006)

---

## Implementation Strategy

### MVP (User Story 1 Only)

1. Phase 1: Confirm baseline build
2. Phase 2: Edit snapcraft.yaml (T002–T005)
3. Phase 3: Build, sideload, smoke test (T006–T013)
4. **STOP and VALIDATE**: Snap installs without `--classic` ✓

### Full Delivery

5. Phase 4: Run review tools (T014–T015)
6. Phase 5: Update docs, confirm test suite (T016–T018)

---

## Notes

- All snapcraft.yaml changes in Phase 2 touch the same file — run sequentially
- The `.snap` build artifact from T006 is reused in both Phase 3 and Phase 4
- No Python source files change; the existing 140-test suite is entirely unaffected
- The `home` interface auto-connects on standard Ubuntu desktop/server (`on-classic: true`); manual connect (T008) is only needed on Ubuntu Core
