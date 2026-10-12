# Quickstart: User Documentation (Diataxis)

**Branch**: `002-diataxis-docs` | **Date**: 2026-02-26

Developer guide for implementing this feature. Read `research.md` for rationale behind each decision.

---

## Prerequisites

- `uv` installed (project package manager).
- Run `uv sync --all-extras` to install dev dependencies.
- Run `cd src && pytest` to confirm the existing test suite passes before starting.

---

## Implementation Order

### Step 1: Validator fix (prerequisite for accurate documentation)

**File**: `src/buddy_scheduler/validator.py`

After the existing `for i, entry in enumerate(data)` loop, add a second pass:

```python
# Cross-reference avoid_buddies entries against known member names
all_names = {m.name for m in members}
for member in members:
    for buddy in member.avoid_buddies:
        if buddy not in all_names:
            raise DataValidationError(
                f"Member '{member.name}' has unrecognised avoid_buddies entry "
                f"'{buddy}' — no member named '{buddy}' exists in the roster"
            )
```

**Tests to add** (`tests/unit/test_validator.py`):
1. `test_avoid_buddies_valid_reference` — member references an existing name → no error
2. `test_avoid_buddies_unknown_name` — member references a non-existent name → `DataValidationError` containing the member name and unrecognised entry
3. `test_avoid_buddies_inactive_member_valid` — member references an inactive member → no error (inactive members are still in the roster)
4. `test_avoid_buddies_self_reference_ignored` — member lists their own name → no error (self-reference has no pairing effect but is not an error)

Run `pytest tests/unit/test_validator.py` to confirm.

---

### Step 2: Create YAML fixtures

**Directory**: `tests/fixtures/`

Create the five fixture files. Content must match what will be shown in the documentation.

**`tests/fixtures/minimal.yaml`** — tutorial example: 4 members, two timezones, no optional fields

```yaml
- name: Alice
  timezone: "UTC+0"

- name: Bob
  timezone: "UTC+0"

- name: Charlie
  timezone: "America/New_York"

- name: Diana
  timezone: "America/New_York"
```

**`tests/fixtures/full-example.yaml`** — reference example demonstrating all 4 fields

```yaml
- name: Alice
  timezone: "UTC+0"

- name: Bob
  timezone: "UTC+0"
  avoid_buddies:
    - Charlie

- name: Charlie
  timezone: "UTC+0"

- name: Diana
  timezone: "America/New_York"

- name: Eve
  timezone: "America/New_York"

- name: Frank
  timezone: "America/New_York"
  active: false
```

**`tests/fixtures/with-absence.yaml`** — absence how-to: one inactive member

```yaml
- name: Alice
  timezone: "UTC+0"

- name: Bob
  timezone: "UTC+0"

- name: Charlie
  timezone: "UTC+0"
  active: false

- name: Diana
  timezone: "America/New_York"
```

**`tests/fixtures/with-avoidance.yaml`** — avoidance how-to: manager/report pair

```yaml
- name: Alice
  timezone: "UTC+0"

- name: Bob
  timezone: "UTC+0"
  avoid_buddies:
    - Alice

- name: Charlie
  timezone: "America/New_York"

- name: Diana
  timezone: "America/New_York"
```

**`tests/fixtures/unknown-avoid-buddy.yaml`** — validator error test

```yaml
- name: Alice
  timezone: "UTC+0"
  avoid_buddies:
    - Alic

- name: Bob
  timezone: "UTC+0"

- name: Charlie
  timezone: "America/New_York"

- name: Diana
  timezone: "America/New_York"
```

---

### Step 3: Write documentation (in priority order)

Write the Markdown files under `docs/`. Use the contracts in `specs/001-buddy-scheduler/contracts/` as the authoritative source for option names, field names, and output format (`cli-schema.md`, `team-roster-schema.yaml`, `result-schema.json`). Use the fixture files for all YAML examples (copy content verbatim from the fixture files).

**Priority order**:
1. `docs/tutorial/getting-started.md` (P1 — unblocks all other docs)
2. `docs/how-to/track-history.md` (P2)
3. `docs/how-to/manage-absences.md` (P2)
4. `docs/how-to/avoid-pairings.md` (P2 — depends on validator fix from Step 1)
5. `docs/reference/cli.md` (P3)
6. `docs/reference/team-yaml.md` (P3)
7. `docs/reference/output-format.md` (P3)
8. `docs/explanation/how-mip-works.md` (P4)

**Tutorial structure** (`getting-started.md`):
1. Prerequisites (Python 3.11+, uv)
2. Install: `uv tool install buddy-scheduler`
3. Install alternative: snap (`sudo snap install buddy-scheduler --classic`)
4. Create a team roster file (show `tests/fixtures/minimal.yaml` content verbatim)
5. Run a dry run: `buddy-scheduler --team team.yaml`
6. Read the output: explain each field from `specs/001-buddy-scheduler/contracts/result-schema.json`

**Each how-to structure** (one task, self-contained after tutorial):
1. Goal — one sentence
2. Prerequisites — only what's not covered in the tutorial
3. Steps — numbered
4. Expected result / verification step

**Reference structure** (lookup-optimised, no narrative):
- Tables for all options/fields
- One or two example invocations per option
- All defaults, types, valid values explicit

**Explanation structure** (`how-mip-works.md`):
1. What problem the tool solves
2. The objective function (weighted penalty sum — narrative description + symbolic formula)
3. Hard constraints (coverage, avoidance — narrative)
4. Sit-out fairness (narrative)
5. Timezone scoring (string similarity — narrative, implications for label consistency)
6. Solver profiles (gap tolerance tradeoff — narrative, refer to reference/cli.md for the table)

---

### Step 4: Write doc example tests

One test file per documentation section. Use Click's `CliRunner`. Each test function name encodes the document and example it validates.

**Test file layout example** (`tests/integration/test_docs_tutorial.py`):

```python
"""Doc example tests for docs/tutorial/getting-started.md."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from buddy_scheduler.cli import main

FIXTURES = Path(__file__).parent.parent / "fixtures"

REQUIRED_SUCCESS_FIELDS = {
    "success", "pairs", "sitting_out",
    "optimization_score", "solve_time",
    "solver_profile", "history_updated",
}


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def test_tutorial_dry_run(runner: CliRunner) -> None:
    """Tutorial example: buddy-scheduler --team minimal.yaml (no history)."""
    result = runner.invoke(main, ["--team", str(FIXTURES / "minimal.yaml")])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert REQUIRED_SUCCESS_FIELDS <= data.keys()
    assert data["success"] is True
    assert data["history_updated"] is False
```

**Test functions to write per file**:

| Test file | Test functions |
|-----------|----------------|
| `test_docs_tutorial.py` | `test_tutorial_dry_run` |
| `test_docs_how_to_history.py` | `test_how_to_history_update`, `test_how_to_history_prune_without_update_warns` |
| `test_docs_how_to_absences.py` | `test_how_to_absence_member_excluded`, `test_how_to_absence_reactivated_member_included` |
| `test_docs_how_to_avoidance.py` | `test_how_to_avoidance_pair_never_appears`, `test_how_to_avoidance_unknown_name_errors` |
| `test_docs_ref_cli.py` | `test_ref_cli_negative_history_weight_errors`, `test_ref_cli_negative_tz_weight_errors`, `test_ref_cli_invalid_solver_profile_errors`, `test_ref_cli_invalid_log_level_errors` |
| `test_docs_ref_output.py` | `test_ref_output_success_fields_present`, `test_ref_output_failure_fields_present`, `test_ref_output_exit_codes` |

---

### Step 5: Verify coverage gate

```bash
cd src && pytest --cov=buddy_scheduler --cov-report=term-missing
```

Coverage must remain ≥ 80%. If it drops, add targeted unit tests to the appropriate `tests/unit/` file.

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Test runner | `click.testing.CliRunner` | No subprocess, no install required, in-process, fast |
| Test location | `tests/integration/` | Doc examples are integration tests; consistent with existing structure |
| Fixture location | `tests/fixtures/` | Single source of truth, accessible to all test types |
| Output assertion depth | Field presence only | Values vary (solve_time, score, pair order); field-presence catches renames/removals |
| MIP explanation | Narrative + formula only | No numeric worked examples (user decision in clarification session) |
| Validator fix | Second-pass cross-reference | First pass builds name set; second pass validates references |
