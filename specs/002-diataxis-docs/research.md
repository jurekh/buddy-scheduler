# Research: User Documentation (Diataxis)

**Branch**: `002-diataxis-docs` | **Date**: 2026-02-26

## Decision 1: Doc Example Test Runner

**Decision**: Use `click.testing.CliRunner` for all CLI doc-example tests.

**Rationale**: CliRunner is Click's official testing utility, already available as a transitive dependency (no new deps needed). It captures stdout/stderr/exit code cleanly, runs in-process without spawning a subprocess, and integrates with pytest without any configuration. The buddy-scheduler test suite already uses it in `tests/contract/` and `tests/integration/`.

**Alternatives considered**:
- `subprocess.run` — requires the package to be installed in the test environment; slower; harder to capture structured output; overkill for a same-process CLI.
- `pytest-codeblocks` / `phmdoctest` / `mktestdocs` — test Python REPL code blocks in Markdown automatically. Not appropriate here: the documentation examples are shell commands (`buddy-scheduler --team ...`), not Python REPL sessions. These plugins have no mechanism to invoke Click CLIs.
- `doctest` — stdlib doctest tests Python `>>>` prompts in docstrings; not applicable to Markdown shell examples.

## Decision 2: Doc Test Location

**Decision**: Add doc example tests to `tests/integration/`, one file per documentation section.

**Rationale**: Documentation examples exercise the full CLI entry point (argument parsing → validation → solver → JSON output), which is the definition of an integration test. Placing them alongside `test_pipeline.py` is consistent with the existing project structure. One file per doc section (e.g., `test_docs_tutorial.py`, `test_docs_how_to_history.py`) makes failures immediately identifiable to a specific document, satisfying FR-018's requirement that failures name the affected document.

**Alternatives considered**:
- New `tests/docs/` module — introduces a fourth test category with no clear distinction from integration tests; would require updating `pyproject.toml` testpaths.
- Single `tests/integration/test_docs_examples.py` — simpler but failure messages require reading test function names to identify the document; marginally less traceable.

## Decision 3: YAML Fixture Sharing

**Decision**: Canonical YAML fixture files in `tests/fixtures/`; documentation inline-quotes their content.

**Rationale**: Fixture files in `tests/fixtures/` are the single source of truth. Tests reference them by path. Documentation shows their content inline (copied into fenced code blocks). This means: if a fixture changes, tests break immediately AND the author must update the doc prose — which is the desired behaviour (any divergence surfaces as a test failure or a visible doc edit).

**Alternatives considered**:
- Fixtures embedded in test code — doubles maintenance (change fixture = change test string + update doc); no single source.
- Docs include/transclude fixture files — not supported by standard Markdown without a site generator; out of scope per the spec assumption (plain Markdown only).

## Decision 4: Structural Field-Presence Check Scope

**Decision**: For success-path CLI invocations, assert that every JSON field documented for that command is present in `json.loads(result.output)`. Do not assert field values (they vary: `solve_time`, `optimization_score`, pair permutations). For error-path invocations, assert `exit_code != 0` and `success == False` and `error` field is present.

**Rationale**: Clarified in spec session (Q2). Exact-value matching is brittle for variable fields and would cause constant false failures. Field-presence catches the real regression risk: a renamed or removed output field. This approach also correctly catches field additions if the docs document a subset of fields (missing field = assertion fails).

**Fields asserted for a successful dry-run invocation** (from `contracts/output-json.md`):
`success`, `pairs`, `sitting_out`, `optimization_score`, `solve_time`, `solver_profile`, `history_updated`

## Decision 5: Validator Fix Approach

**Decision**: Add a second pass in `validator.py` after the member list is built to cross-reference all `avoid_buddies` entries against the full set of member names, raising `DataValidationError` for any unrecognised name.

**Rationale**: The first pass builds `seen_names` as members are parsed. A second cross-reference pass after the loop is simple, readable, and consistent with the existing two-step validation pattern (structural parse → semantic check). Raising `DataValidationError` (exit code 1) is consistent with how all other validation failures are handled.

**Error message format**: `"Member '{name}' has unrecognised avoid_buddies entry '{entry}' — no member named '{entry}' exists in the roster"` — identifies the member, the bad entry, and the cause.

**Alternatives considered**:
- Validate during the first pass — not possible because a member can reference another member who appears later in the file.
- Warn instead of error — rejected per spec (user confirmed validation error, not silent ignore).
- Validate in `mip.py` before solve — validator is the correct boundary; solver should never see invalid input.

## Decision 6: Contract Ownership

**Decision**: Do not create new contract files in `specs/002-diataxis-docs/contracts/`. Use and update the existing contracts in `specs/001-buddy-scheduler/contracts/`.

**Rationale**: The contracts in `specs/001-buddy-scheduler/contracts/` describe the tool's interface — they are not tied to that feature's implementation work, they are the ongoing source of truth for the whole project. Duplicating them under 002 would create two documents that must be kept in sync, inviting divergence. The correct pattern is to update the authoritative 001 contracts when the interface changes (which this feature does, via the `avoid_buddies` validation fix).

**Changes made to 001 contracts as part of this feature**:
- `team-roster-schema.yaml`: fixed stale `avoid_buddies` comment ("silently ignored" → validation error); added the new `DataValidationError` case to the validation errors list.
- `result-schema.json`: removed the non-existent `timestamp` field; removed stale fallback `solver_profile` encoding and fallback example; added validation failure example showing the `avoid_buddies` error message format.

**Also resolved**: `specs/001-buddy-scheduler/contracts/` previously contained two CLI contract files (`cli.md` and `cli-schema.md`). They were merged into `cli-schema.md` (more complete) and `cli.md` was deleted. Corrections made during merge: fixed `--prune-history` behaviour (emits WARNING, not a validation error); corrected the auto-inferred history path (`team.history.json`, not `team_history.json`); removed stale fallback rows from the logging contract; removed inline JSON/YAML/history schema sections that now live in their own files.

## Decision 7: Diataxis File Organisation

**Decision**: `docs/{tutorial,how-to,reference,explanation}/` with one Markdown file per document.

**Files**:
- `docs/tutorial/getting-started.md` — installation, first team.yaml, first dry run
- `docs/how-to/track-history.md` — --update-history, inferred path, --prune-history
- `docs/how-to/manage-absences.md` — active field, marking inactive, reactivating
- `docs/how-to/avoid-pairings.md` — avoid_buddies, manager/report example, error handling
- `docs/reference/cli.md` — all 8 CLI options, types, defaults, interactions
- `docs/reference/team-yaml.md` — all 4 YAML fields, types, defaults, constraints
- `docs/reference/output-format.md` — all JSON output fields, success and failure schemas, exit codes
- `docs/explanation/how-mip-works.md` — objective function, hard constraints, timezone scoring, solver profiles

**Rationale**: One file per document keeps each Diataxis type self-contained and maps cleanly to one test file (or one section in a test file). The reference `output-format.md` consolidates output fields and exit codes (FR-009 + FR-010) into one reference page since they describe the same interaction boundary.
