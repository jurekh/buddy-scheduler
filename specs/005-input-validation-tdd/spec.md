# Feature Specification: Input Validation — Invalid Paths and Malformed Files

**Feature Branch**: `005-input-validation-tdd`
**Created**: 2026-03-03
**Status**: Draft
**Input**: Add handling of invalid input paths and malformed input files using TDD

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Team file path validation covers all invalid path kinds (Priority: P1)

A developer running the scheduler with a mis-specified `--team` argument needs an
immediate, structured error rather than a crash or silent misbehaviour. Currently
the tool handles a missing file and a malformed YAML document, but it does not
explicitly handle the case where the supplied path resolves to a directory instead
of a file — a common copy-paste mistake. The tool must detect this case and emit a
clear, machine-readable failure before attempting to parse the path as a roster.

**Why this priority**: The team file is a required argument on every run. Any
unhandled path kind causes an unstructured failure, which breaks downstream
automation that parses JSON output from the CLI.

**Independent Test**: Run the CLI with a directory path as `--team`. Expect exit
code 1 and a JSON `{"success": false, "error": "..."}` body on stdout. No other
tests are needed to validate this story.

**Acceptance Scenarios**:

1. **Given** the `--team` argument points to a directory (not a file), **When** the
   CLI is invoked, **Then** exit code is 1 and stdout contains a JSON object with
   `"success": false` and a human-readable `"error"` message identifying the path
   as a directory.
2. **Given** a previously covered case (file does not exist), **When** the CLI is
   invoked, **Then** behaviour is unchanged: exit code 1, JSON failure output.
3. **Given** the `--team` argument points to a zero-byte file, **When** the CLI is
   invoked, **Then** exit code is 1 and the error message states the file is empty.

---

### User Story 2 - History file validation catches directories and malformed content (Priority: P2)

A developer supplying a `--history` path that is a directory, an empty file, or a
file containing invalid data needs a clear failure with a structured error message.
At present the tool loads a history file only when the path exists, but does not
handle the case where the path resolves to a directory or where the file contains
structurally invalid content (e.g., valid JSON but the wrong schema, or a file that
is not JSON at all). These cases currently produce unhandled exceptions or silent
wrong results instead of exit code 1 with a JSON error body.

**Why this priority**: History files are optional but widely used in automation
pipelines. Silent failures on malformed history silently drop scheduling
constraints, causing repeated pairings that erode user trust.

**Independent Test**: Run the CLI with `--history` pointing to a directory, then
with `--history` pointing to a file containing non-JSON text. Both must exit 1 with
structured JSON errors. No production-code changes to the team loader are needed.

**Acceptance Scenarios**:

1. **Given** the `--history` path points to a directory, **When** the CLI runs,
   **Then** exit code is 1 and stdout contains `"success": false` with an error
   describing the path as a directory.
2. **Given** the `--history` path points to a file containing text that is not
   valid JSON (e.g., plain text or YAML), **When** the CLI runs, **Then** exit
   code is 1 and the error message identifies the parse failure.
3. **Given** the `--history` path points to a valid JSON file whose top-level
   structure is not the expected schema (e.g., a JSON array instead of an object
   with the required keys), **When** the CLI runs, **Then** exit code is 1 and
   the error message describes the schema mismatch.
4. **Given** the `--history` path points to a zero-byte file, **When** the CLI
   runs, **Then** exit code is 1 with a message indicating the file is empty.

---

### User Story 3 - Numeric parameter boundary values are accepted or rejected correctly (Priority: P2)

A developer passing weight arguments at their exact lower boundary (`0.0`) needs
confirmation that the value is accepted as valid, not rejected as negative. A
developer who inadvertently passes a non-numeric string needs a clear validation
error rather than an opaque type error. Neither case is currently covered by tests,
leaving the boundary behaviour undocumented.

**Why this priority**: Zero-weight arguments are a legitimate and documented use
case (disabling history or timezone penalty); confirming their acceptance also
validates the boundary of the negative-value rejection already in place.

**Independent Test**: Run the CLI with `--history-weight 0.0` and `--tz-weight 0.0`
on a valid team file; both must succeed. Run with a non-numeric string; must exit
with a clear error. No changes to the scheduler core are required.

**Acceptance Scenarios**:

1. **Given** `--history-weight 0.0` and a valid team file, **When** the CLI runs,
   **Then** exit code is 0 and the result is a valid pairing.
2. **Given** `--tz-weight 0.0` and a valid team file, **When** the CLI runs,
   **Then** exit code is 0 and the result is a valid pairing.
3. **Given** `--history-weight` is supplied a non-numeric string (e.g., `"high"`),
   **When** the CLI runs, **Then** exit code is non-zero and the output indicates
   the value is invalid.
4. **Given** `--tz-weight` is supplied a non-numeric string (e.g., `"medium"`),
   **When** the CLI runs, **Then** exit code is non-zero and the output indicates
   the value is invalid.

---

### Edge Cases

- What happens when `--team` path contains a null byte or other control characters?
- What happens when `--history` points to a symlink that resolves to a directory?
- What happens when `--history` points to a JSON file with `null` as the top-level value?
- What happens when `--history-weight` or `--tz-weight` is `+Inf` or `NaN`?
- What happens when the history file exists but is unreadable due to permissions?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When `--team` resolves to an existing directory (not a regular file),
  the CLI MUST exit with code 1 and emit a JSON `{"success": false, "error": "..."}` body
  on stdout describing the path as a directory.
- **FR-002**: When `--history` resolves to an existing directory (not a regular file),
  the CLI MUST exit with code 1 and emit a JSON error body describing the path as a directory.
- **FR-003**: When `--history` points to a file whose content cannot be parsed as
  the expected structured format (invalid syntax or wrong schema), the CLI MUST exit
  with code 1 and emit a JSON error body identifying the nature of the parse or
  schema failure.
- **FR-004**: When `--history` points to a zero-byte file, the CLI MUST exit with
  code 1 and emit a JSON error body stating the file is empty.
- **FR-005**: When `--history-weight` or `--tz-weight` is supplied the value `0.0`,
  the CLI MUST accept it as valid and produce a successful pairing (exit code 0).
- **FR-006**: When `--history-weight` or `--tz-weight` is supplied a non-numeric
  string, the CLI MUST exit with a non-zero exit code and indicate the value is invalid.
- **FR-007**: All new validation checks MUST be covered by tests written before or
  alongside any production-code changes (TDD order: failing test first, minimal fix,
  passing test confirms the fix).
- **FR-008**: All new tests MUST be runnable within the default test run (no
  `slow` marker required), completing alongside the existing unit and contract tests.
- **FR-009**: Test coverage for the CLI and history loader modules MUST NOT decrease
  below the current gate (80%) after these changes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Each identified uncovered path-validation case (directory as team
  file, directory as history file, non-parseable history file, empty history file)
  has a dedicated test that fails before any production-code fix and passes after.
- **SC-002**: Both zero-value weight scenarios (`--history-weight 0.0` and
  `--tz-weight 0.0`) are captured by passing tests, confirming the lower boundary
  is accepted and negative-value rejection is bounded correctly.
- **SC-003**: The full default test suite (excluding slow-marked tests) passes
  without regression after all new tests and corresponding fixes are applied.
- **SC-004**: Test coverage does not fall below 80% for any affected module.
- **SC-005**: Every new failure scenario emits a JSON body on stdout that is
  parseable and contains `"success": false` and a non-empty `"error"` string,
  consistent with the existing error output contract.

## Assumptions

- The existing error output contract (JSON on stdout, `"success": false`,
  `"error"` string, exit code 1) is stable and applies to all new failure cases.
- A path resolving to a directory is a distinct error kind from "file not found"
  and warrants its own message so operators can diagnose the mistake without
  inspecting the file system manually.
- Zero (`0.0`) is a valid value for both weight parameters; the existing negative-
  value rejection boundary is `< 0.0`, not `≤ 0.0`.
- The history file schema (an object with `pair_counts` and `sit_out_counts` keys)
  is stable; schema validation needs to detect only a missing top-level required key
  or an incorrect root type — exhaustive field-level validation is out of scope.
- Non-numeric string values for weight parameters may produce exit code 2 (argument
  parsing error) rather than 1; tests assert non-zero rather than a specific value.
- Symlinks are followed by the OS before path-kind checks are applied; a symlink
  to a directory is treated identically to a direct directory path.
