# Data Model: User Documentation (Diataxis)

**Branch**: `002-diataxis-docs` | **Date**: 2026-02-26

This feature introduces no new persistent data model. It delivers documentation files, test fixtures, and a validator rule extension. This document describes those artifacts as entities.

---

## Documentation Files

Each Markdown file is a `DocumentationFile` with a fixed Diataxis type that constrains its content.

| Entity | Path | Diataxis Type | Primary FR |
|--------|------|--------------|------------|
| Getting Started tutorial | `docs/tutorial/getting-started.md` | Tutorial | FR-001, FR-002 |
| Track History how-to | `docs/how-to/track-history.md` | How-to | FR-003 |
| Manage Absences how-to | `docs/how-to/manage-absences.md` | How-to | FR-004 |
| Avoid Pairings how-to | `docs/how-to/avoid-pairings.md` | How-to | FR-005 |
| CLI reference | `docs/reference/cli.md` | Reference | FR-006, FR-007 |
| team.yaml format reference | `docs/reference/team-yaml.md` | Reference | FR-008 |
| Output & exit codes reference | `docs/reference/output-format.md` | Reference | FR-009, FR-010 |
| MIP explanation | `docs/explanation/how-mip-works.md` | Explanation | FR-011–FR-014 |

**Constraints**:
- A Tutorial file MUST contain a linear walkthrough; no reference tables or conceptual digressions.
- A How-to file MUST address exactly one task; no tutorial steps or algorithm explanations.
- A Reference file MUST be structured for lookup (tables, lists, definitions); no narrative prose or step-by-step instructions.
- An Explanation file MUST be conceptual narrative only; no step-by-step instructions or exact command syntax (FR-011: narrative and formula only, no numeric worked examples).

---

## Doc Examples

A `DocExample` is a testable code block within a documentation file.

**Attributes**:
- `document`: path to the containing documentation file
- `type`: `cli-invocation` | `yaml-file`
- `command_args`: list of CLI arguments (for `cli-invocation`)
- `content`: YAML text (for `yaml-file`)
- `expected_exit_code`: 0, 1, or 2
- `documented_fields`: list of JSON output field names that must be present (for `cli-invocation` with exit code 0)

**Constraints**:
- Every `cli-invocation` example MUST use exact current option names (FR-016).
- Every `yaml-file` example MUST be loadable by the current validator without error (unless the example is explicitly demonstrating an error case).
- Every `DocExample` MUST have a corresponding test function in `tests/integration/` (FR-018).

**Documented fields for a success-path invocation** (from output-json.md contract):
`success`, `pairs`, `sitting_out`, `optimization_score`, `solve_time`, `solver_profile`, `history_updated`

---

## YAML Fixtures

Canonical YAML files in `tests/fixtures/` are the single source of truth for YAML examples shown in the documentation.

| Fixture | Path | Use Case | Demonstrates |
|---------|------|----------|-------------|
| `minimal.yaml` | `tests/fixtures/minimal.yaml` | Tutorial dry run | 4 members, timezone only |
| `full-example.yaml` | `tests/fixtures/full-example.yaml` | Reference & avoidance how-to | All 4 fields: name, timezone, active, avoid_buddies |
| `with-absence.yaml` | `tests/fixtures/with-absence.yaml` | Absence how-to | One member with `active: false` |
| `with-avoidance.yaml` | `tests/fixtures/with-avoidance.yaml` | Avoidance how-to | One `avoid_buddies` pair (manager/report) |
| `unknown-avoid-buddy.yaml` | `tests/fixtures/unknown-avoid-buddy.yaml` | Validator error test | `avoid_buddies` entry that references a non-existent name |

**Constraints**:
- All fixtures MUST be valid YAML.
- All fixtures except `unknown-avoid-buddy.yaml` MUST pass validator validation without error.
- `unknown-avoid-buddy.yaml` MUST trigger a `DataValidationError` identifying the unrecognised name.
- Fixture content shown in documentation prose MUST match the fixture file on disk exactly.

---

## Validator Rule Extension

The `load_team_roster` function in `src/buddy_scheduler/validator.py` gains one new semantic check after the existing first-pass parsing loop.

**New rule**: After all members are parsed into the `members` list, cross-reference every `avoid_buddies` entry against the set of all member names. If any entry does not match, raise `DataValidationError`.

**Error message format**:
```
Member '{name}' has unrecognised avoid_buddies entry '{entry}' — no member named '{entry}' exists in the roster
```

**State transitions** (validator outcomes):

| Input condition | Before fix | After fix |
|----------------|-----------|-----------|
| `avoid_buddies` name matches a roster member | Constraint respected | Constraint respected (no change) |
| `avoid_buddies` name does not match any roster member | Silently ignored; constraint not applied | `DataValidationError` raised; exit code 1 |

**Test cases to add** (extend `tests/unit/test_validator.py`):
1. Valid `avoid_buddies` referencing an existing member → no error
2. `avoid_buddies` referencing a name not in the roster → `DataValidationError` with the unrecognised name in the message
3. `avoid_buddies` referencing a member who is inactive → valid (inactive members are in the roster)
4. Multiple unrecognised entries → all unrecognised names reported (or first encountered — see contract)
