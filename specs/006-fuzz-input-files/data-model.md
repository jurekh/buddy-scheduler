# Data Model: Fuzz Testing for Team Roster and History Files

**Branch**: `006-fuzz-input-files`
**Created**: 2026-03-03

---

## Overview

This feature introduces no new data entities. It adds tests that verify the
exception-safety contracts of two existing loaders. The relevant entities are
already defined in `src/buddy_scheduler/models.py`.

---

## Entities under test (existing)

### `TeamMember` (read-only during fuzz)

| Field | Type | Constraint |
|-------|------|-----------|
| `name` | `str` | non-empty, unique within roster |
| `timezone` | `str` | non-empty |
| `active` | `bool` | defaults to `True` |
| `avoid_buddies` | `list[str]` | each entry must match a `name` in the roster |

The fuzz tests for `load_team_roster` verify that any file content either produces
a valid `list[TeamMember]` (satisfying the above constraints) or raises a
`FileLoadError` or `DataValidationError`.

### `PairingHistory` (read-only during fuzz)

| Field | Type | Constraint |
|-------|------|-----------|
| `matrix` | `dict[str, dict[str, int]]` | symmetric, all counts ≥ 0 |
| `sit_out_counts` | `dict[str, int]` | all counts ≥ 0 |

The fuzz tests for `load_history` verify the same contract for any file content.

---

## Exception hierarchy (safety contract)

```text
BuddySchedulerError                ← all domain errors must be one of these
├── FileLoadError                  ← file missing, unreadable, empty, wrong format
├── DataValidationError            ← structurally / semantically invalid content
├── FileSaveError                  ← (not exercised by fuzz tests)
└── OptimizationError              ← (not exercised by fuzz tests)
```

**Contract enforced by the fuzz tests**: for any file content supplied to
`load_team_roster` or `load_history`, the only observable outcomes are:

1. Return a valid result (`list[TeamMember]` or `PairingHistory`).
2. Raise `FileLoadError`.
3. Raise `DataValidationError`.

Any other exception type (including `yaml.YAMLError`, `json.JSONDecodeError`,
`UnicodeDecodeError`, `RecursionError`, `MemoryError`, `OSError`, etc.) propagating
out of the loader constitutes a test failure.

---

## No new entities introduced

The hypothesis test infrastructure (`_ROSTER_CONTENT`, `_HISTORY_CONTENT` strategies,
`@settings`) is test-only code and introduces no entities that affect the production data
model.
