# Implementation Plan: User Documentation (Diataxis)

**Branch**: `002-diataxis-docs` | **Date**: 2026-02-26 | **Spec**: `specs/002-diataxis-docs/spec.md`
**Input**: Feature specification from `specs/002-diataxis-docs/spec.md`

## Summary

Deliver Diataxis-structured user documentation for buddy-scheduler (tutorial, four how-to guides, three reference pages, one explanation), covering all eight CLI options, all four `team.yaml` fields, the full JSON output schema, and the MIP algorithm. Every CLI invocation and `team.yaml` example in the docs is covered by an automated test that runs as part of the default `pytest` invocation. A prerequisite implementation fix extends `validator.py` to raise `DataValidationError` when an `avoid_buddies` entry names a roster member that does not exist.

No new runtime dependencies. All test infrastructure uses existing tools: `click.testing.CliRunner`, `pytest`, and YAML fixtures under `tests/fixtures/`.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: Click ≥ 8.1 (CliRunner for doc tests), PyYAML ≥ 6.0, PuLP ≥ 2.7, psutil ≥ 5.9 — all existing; no new runtime deps
**Storage**: Markdown files in `docs/`; shared YAML fixtures in `tests/fixtures/`
**Testing**: pytest + `click.testing.CliRunner` (in-process, no subprocess)
**Target Platform**: Linux primary (snap); Python package path covers other platforms
**Project Type**: CLI tool — documentation + test coverage extension + validator fix
**Performance Goals**: N/A (documentation deliverable; tests must complete within default `pytest` run)
**Constraints**: No new runtime deps; doc example tests auto-included in default `pytest` invocation; coverage must remain ≥ 80%
**Scale/Scope**: 8 documentation Markdown files, 5 YAML fixtures, ~17 test functions, 1 validator rule extension

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Type Safety & Validated Inputs | ✅ Pass | Validator fix uses `DataValidationError` (typed exception); no bare exceptions. Doc tests use typed `CliRunner` return. |
| II. Data Integrity | ✅ Pass | No new persistent state introduced. Validator fix raises before computation, preventing malformed avoidance constraints from reaching the solver. |
| III. Comprehensive Testing | ✅ Pass | Doc example tests added to `tests/integration/`; run in default `pytest` invocation; validator unit tests extended; coverage gate ≥ 80% enforced. |
| IV. Transparent Operations | ✅ Pass | Documentation explains and reinforces the stdout JSON / stderr diagnostics split. |
| V. Explicit Failure Reporting | ✅ Pass | Validator fix makes `avoid_buddies` mismatches an explicit error rather than a silent no-op. Docs document the error message and how to resolve it. |

**Post-design re-check** (after Phase 1): All principles remain satisfied. No new architectural patterns introduced; feature is additive (docs + tests + one validator rule).

## Project Structure

### Documentation (this feature)

```text
specs/002-diataxis-docs/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (deferred to 001-buddy-scheduler/contracts/ per Decision 6)
└── tasks.md             # Phase 2 output (/speckit.tasks — not created by /speckit.plan)
```

### Source Code (repository root)

```text
docs/
├── tutorial/
│   └── getting-started.md          # FR-001, FR-002
├── how-to/
│   ├── track-history.md            # FR-003
│   ├── manage-absences.md          # FR-004
│   └── avoid-pairings.md           # FR-005
├── reference/
│   ├── cli.md                      # FR-006, FR-007
│   ├── team-yaml.md                # FR-008
│   └── output-format.md            # FR-009, FR-010
└── explanation/
    └── how-mip-works.md            # FR-011–FR-014

tests/
├── fixtures/
│   ├── minimal.yaml                # Tutorial dry run (4 members, timezone only)
│   ├── full-example.yaml           # Reference & avoidance how-to (all 4 fields)
│   ├── with-absence.yaml           # Absence how-to (one inactive member)
│   ├── with-avoidance.yaml         # Avoidance how-to (manager/report pair)
│   └── unknown-avoid-buddy.yaml    # Validator error test (non-existent avoid_buddies name)
└── integration/
    ├── test_docs_tutorial.py
    ├── test_docs_how_to_history.py
    ├── test_docs_how_to_absences.py
    ├── test_docs_how_to_avoidance.py
    ├── test_docs_ref_cli.py
    └── test_docs_ref_output.py

src/buddy_scheduler/
└── validator.py                    # Extend: second-pass avoid_buddies cross-reference check
```

**Structure Decision**: Single-project layout (existing `src/`, `tests/`). Documentation files go under `docs/` at the repository root, organised by Diataxis type. Test fixtures are in a new `tests/fixtures/` directory (shared across all test types). No new packages or modules; `validator.py` extended in place.

**Contract ownership**: No new files under `specs/002-diataxis-docs/contracts/`. The authoritative contracts live in `specs/001-buddy-scheduler/contracts/` and were updated as part of this feature's research phase (see `research.md` Decision 6).
