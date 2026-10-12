# Implementation Plan: Snap Strict Confinement

**Branch**: `003-snap-strict` | **Date**: 2026-02-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/003-snap-strict/spec.md`

## Summary

Switch `snap/snapcraft.yaml` from `confinement: classic` to `confinement: strict`
by removing the classic-only override-build workaround, removing the now-redundant
PYTHONPATH/PATH environment overrides, and adding `plugs: [home]` to the app. Update
the getting-started tutorial to drop `--classic` from the snap install command. No
Python source changes are required.

## Technical Context

**Language/Version**: Python 3.11 (unchanged); snapcraft 8.x; base: core24
**Primary Dependencies**: snapcraft Python plugin (built-in); no new runtime deps
**Storage**: N/A — packaging change only; existing file I/O is unchanged
**Testing**: snapcraft build + sideload smoke test; existing pytest suite unchanged
**Target Platform**: Linux (snap package); core24 base snap
**Project Type**: CLI packaging change
**Performance Goals**: N/A
**Constraints**: Must install without `--classic`; `home` interface covers all
required file access (`$HOME` visible files); dotfiles out of scope
**Scale/Scope**: Two files changed — `snap/snapcraft.yaml` and
`docs/tutorial/getting-started.md`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Type Safety & Validated Inputs | PASS | No Python code changes |
| II. Data Integrity | PASS | No changes to file write paths |
| III. Comprehensive Testing | PASS | No logic changes; snap build verified via quickstart; existing 80% coverage maintained |
| IV. Transparent Operations | PASS | No changes to stdout/stderr routing |
| V. Explicit Failure Reporting | PASS | Existing DataValidationError on file-not-found already handles EPERM from confinement; no new error paths needed |

No violations. Complexity Tracking table not required.

## Project Structure

### Documentation (this feature)

```text
specs/003-snap-strict/
├── plan.md         # This file
├── research.md     # Phase 0 output
├── quickstart.md   # Phase 1 output — build and smoke test guide
└── tasks.md        # Phase 2 output (/speckit.tasks command)
```

### Source Code (files changed by this feature)

```text
snap/
└── snapcraft.yaml          # confinement, plugs, remove override-build and env vars

docs/
└── tutorial/
    └── getting-started.md  # remove --classic from snap install command
```

No new source files. No new test files. The existing pytest suite is unchanged.

**Structure Decision**: Single-project layout. All changes are contained to
`snap/snapcraft.yaml` and one documentation page.
