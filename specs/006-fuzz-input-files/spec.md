# Feature Specification: Fuzz Testing for Team Roster and History Files

**Feature Branch**: `006-fuzz-input-files`
**Created**: 2026-03-03
**Status**: Draft
**Input**: Fuzz-test team.yaml and history.json

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Team roster parser never crashes on arbitrary content (Priority: P1)

A developer needs confidence that feeding any possible file content to the team
roster loader — whether random bytes, adversarially crafted YAML, deeply nested
structures, Unicode edge cases, or very large strings — will never produce an
unhandled exception, segfault, infinite loop, or memory exhaustion. The loader
must always either return a valid list of members or raise one of the two defined
domain exceptions (`FileLoadError` or `DataValidationError`). No other outcome
is acceptable.

**Why this priority**: The team roster is the only required input to the scheduler.
A crash or hang on malformed content in an automated pipeline would block all
scheduling operations with no actionable output, violating the structured-error
contract that downstream automation depends on.

**Independent Test**: Run the fuzz tests for the team roster loader in isolation.
For a large number of automatically generated inputs, every invocation must
terminate and every raised exception must be a `FileLoadError` or
`DataValidationError`. Zero unhandled exceptions or hangs constitutes a pass.

**Acceptance Scenarios**:

1. **Given** a file containing arbitrary random bytes (including non-UTF-8 sequences),
   **When** the team roster loader is called, **Then** it either returns a valid
   member list or raises `FileLoadError` or `DataValidationError` — no other
   exception propagates.
2. **Given** a file containing valid YAML but with unexpected root types (a string,
   an integer, a deeply nested mapping, a sequence of non-mappings), **When** the
   loader is called, **Then** it raises `FileLoadError` or `DataValidationError`
   and terminates promptly.
3. **Given** a file containing YAML with extreme values (empty strings for required
   fields, strings of length 10 000, Unicode control characters, null bytes within
   strings), **When** the loader is called, **Then** it either accepts the input as
   valid or raises a typed domain exception.
4. **Given** a file containing deeply nested YAML (nesting depth > 100), **When**
   the loader is called, **Then** it terminates without stack overflow or hang.
5. **Given** a valid-looking YAML member list with generated `name`, `timezone`,
   `active`, and `avoid_buddies` values that straddle boundary conditions (empty
   name, boolean-like strings for `active`, references to non-existent members in
   `avoid_buddies`), **When** the loader is called, **Then** it either succeeds or
   raises `DataValidationError`.

---

### User Story 2 - History store parser never crashes on arbitrary content (Priority: P1)

A developer needs the same crash-free guarantee for the history file loader. Any
content supplied as a history file — random bytes, truncated JSON, valid JSON with
unexpected structure or value types, or pathological numeric values — must produce
either a valid `PairingHistory` result or a typed domain exception.

**Why this priority**: History files are written by the tool itself but may be
manually edited or corrupted by external processes. A crash on a corrupt history
file would block every scheduling run that references it, with no way to recover
without manual intervention.

**Independent Test**: Run the fuzz tests for the history loader in isolation. For
a large number of generated inputs, every invocation terminates and raises only
`FileLoadError` or `DataValidationError`. Zero unhandled exceptions constitutes
a pass.

**Acceptance Scenarios**:

1. **Given** a file containing arbitrary bytes, **When** the history loader is
   called, **Then** it either returns a valid `PairingHistory` or raises
   `FileLoadError` or `DataValidationError`.
2. **Given** a file containing valid JSON with unexpected root types (array, string,
   number, boolean, null), **When** the loader is called, **Then** it raises
   `DataValidationError` — it does not silently return an empty history.
3. **Given** a file containing JSON with the expected `pair_counts` and
   `sit_out_counts` keys but with generated values (negative counts, asymmetric
   matrices, non-integer values, deeply nested objects), **When** the loader is
   called, **Then** it either validates successfully or raises `DataValidationError`
   with a descriptive message.
4. **Given** a file containing valid JSON exceeding 1 MB in size, **When** the
   loader is called, **Then** it terminates within a reasonable time without
   memory exhaustion.
5. **Given** a file containing JSON with Unicode member names including right-to-left
   markers, zero-width spaces, or surrogate pairs, **When** the loader is called,
   **Then** it either accepts the names or raises `DataValidationError` — it does
   not crash or raise an encoding error.

---

### User Story 3 - CLI end-to-end: any file content results in exit 0 or exit 1 only (Priority: P2)

A developer needs confidence that when the CLI is invoked with any arbitrarily
generated content for `--team` or `--history`, it always exits with code 0
(success) or 1 (domain error), never with code 2 (unhandled argument error),
an unhandled exception traceback, or a hang. The JSON error contract on stdout
must be honoured for every non-zero exit.

**Why this priority**: Automation systems parse the CLI's JSON stdout and inspect
the exit code to determine success or failure. Any deviation from the documented
exit-code contract or any non-JSON on stdout breaks those pipelines. US1 and US2
cover the library layer; this story closes the gap at the process boundary.

**Independent Test**: Invoke the CLI with fuzz-generated team file content (valid
team file path required; `--history` content fuzzed separately). For every
invocation, assert: exit code is 0 or 1, and if non-zero, stdout parses as JSON
with `"success": false`.

**Acceptance Scenarios**:

1. **Given** the CLI is invoked with a `--team` file containing arbitrary content,
   **When** the process completes, **Then** exit code is 0 or 1, and stdout is
   always valid JSON.
2. **Given** the CLI is invoked with a valid team file and a `--history` file
   containing arbitrary content, **When** the process completes, **Then** exit
   code is 0 or 1, and if 1 then stdout contains `"success": false` and `"error"`.
3. **Given** arbitrary content that happens to parse as a valid YAML list of
   members with all required fields, **When** the CLI is invoked, **Then** exit
   code is 0 and a pairing is produced.

---

### Edge Cases

- What happens when the YAML file contains a Python-specific tag (e.g., `!!python/object`) and `yaml.safe_load` is used — is it safely rejected?
- What happens when the JSON history file contains `NaN` or `Infinity` literals (not valid JSON, but accepted by some parsers)?
- What happens when member names in the history file contain characters that are invalid in YAML but valid in JSON (and vice versa)?
- What happens when `avoid_buddies` lists are very long (hundreds of entries)?
- What happens when the JSON history matrix contains integer keys instead of string keys?
- What happens when a generated team has duplicate names that differ only in Unicode normalisation (e.g., `é` as a precomposed vs decomposed character)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: For every input supplied to the team roster loader, the loader MUST
  either return a valid result or raise `FileLoadError` or `DataValidationError`.
  No other exception type may propagate.
- **FR-002**: For every input supplied to the history file loader, the loader MUST
  either return a valid result or raise `FileLoadError` or `DataValidationError`.
  No other exception type may propagate.
- **FR-003**: The fuzz tests MUST exercise a minimum of 100 distinct generated
  inputs per loader per run, covering random bytes, structurally valid but
  semantically invalid content, extreme string values, and type-boundary inputs.
- **FR-004**: All fuzz tests MUST be tagged so they can be excluded from the
  default fast test run and run explicitly as a separate suite.
- **FR-005**: Fuzz tests MUST be deterministic when run with a fixed seed,
  enabling reproduction of any discovered failure.
- **FR-006**: The fuzz test suite MUST include at least one test that confirms
  YAML files containing Python-specific object tags are rejected (not executed),
  verifying that the safe-load mode is enforced.
- **FR-007**: For US3, the CLI fuzz tests MUST assert that every invocation
  terminates with exit code 0 or 1 and that every non-zero exit produces a
  parseable JSON body on stdout.
- **FR-008**: Any input that causes the loader or CLI to hang (not terminate
  within a defined wall-clock timeout) MUST be treated as a test failure.
- **FR-009**: Coverage of the team roster and history loader modules MUST NOT
  fall below the existing gate (80%) after the fuzz tests are added.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero unhandled exceptions observed across the entire fuzz corpus for
  both loaders across 3 consecutive CI runs.
- **SC-002**: Zero hangs (runs exceeding the per-input timeout) observed across
  the fuzz corpus in 3 consecutive CI runs.
- **SC-003**: The YAML safe-load enforcement test passes: a Python-tagged YAML
  input is rejected without executing the tag, confirmed in every run.
- **SC-004**: The fuzz test suite completes within 3 minutes when run on standard
  CI hardware with the default corpus size (≥ 100 inputs per loader).
- **SC-005**: Any future change to the loaders that introduces a regression (a
  previously safe input now raising an unhandled exception) is caught within the
  same CI run.
- **SC-006**: Overall test coverage does not fall below 80% after the fuzz suite
  is added.

## Assumptions

- The loader functions (`load_team_roster`, `load_history`) are the primary targets;
  the CLI fuzz tests (US3) are additive and call the same code paths.
- "No other exception type may propagate" means the test framework must explicitly
  catch `Exception` and assert it is an instance of `FileLoadError` or
  `DataValidationError` (both subclasses of `BuddySchedulerError`).
- A "hang" is defined as any single-input invocation that does not return within
  5 seconds; this bound is generous relative to typical parse times (< 100 ms) and
  avoids false positives from CI scheduling jitter.
- Property-based / generative testing is assumed as the implementation approach;
  hand-crafted mutation corpora are out of scope.
- The generated corpus includes at minimum: random bytes, ASCII text, valid YAML/JSON
  with generated values, invalid YAML/JSON, deeply nested structures (depth 50+),
  very long strings (> 10 000 characters), and Unicode edge cases.
- `yaml.safe_load` is already used in the production code; the fuzz tests verify
  it remains so and that no unsafe tags bypass the parser.
- Fuzz tests share the same `@pytest.mark.slow` marker convention already established
  in this project, placing them outside the default fast test run.
