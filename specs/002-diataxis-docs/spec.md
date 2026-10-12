# Feature Specification: User Documentation (Diataxis)

**Feature Branch**: `002-diataxis-docs`
**Created**: 2026-02-26
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - New User Gets Started (Priority: P1)

A first-time user arrives at the project and can go from zero to generating their first buddy pairing by following a tutorial. The tutorial covers installation (as a Python package and as a snap), creating a minimal team roster file, running the tool without saving history (dry run), and understanding the output.

**Why this priority**: Without a getting-started path, no new user can adopt the tool. This is the entry point for all other documentation and delivers immediate, concrete value on its own.

**Independent Test**: A person unfamiliar with the tool follows the tutorial start to finish and generates valid pairing output without consulting any other documentation or asking for help.

**Acceptance Scenarios**:

1. **Given** a new user with no prior knowledge, **When** they follow the tutorial from beginning to end, **Then** they have a working installation and have generated and read their first buddy pairing output.
2. **Given** the tutorial's Python package installation steps, **When** a user follows them, **Then** the `buddy-scheduler` command is available in their terminal.
3. **Given** the tutorial's snap installation steps, **When** a user follows them, **Then** the `buddy-scheduler` command is available and produces the same results as the package install.
4. **Given** the tutorial's team file section, **When** a user creates the described minimal roster, **Then** the tool accepts it without validation errors.
5. **Given** a complete tutorial walk-through, **When** the user runs the dry-run command (without `--update-history`), **Then** they see structured pairing output and the tutorial explains what each output field means.

---

### User Story 2 - Coordinator Tracks History Across Rounds (Priority: P2)

A team coordinator who has completed the tutorial wants to carry forward pairing history between rounds so the same pairs are not repeated. They find a how-to guide explaining how to enable history storage, where the history file is created, and how to remove stale entries when team members leave.

**Why this priority**: History-aware rotation is the primary value of the tool beyond basic pairing. Without this guide, coordinators either skip history (losing rotation benefit) or discover it by trial and error.

**Independent Test**: A coordinator who has already run a dry-run pairing follows this guide and successfully runs two consecutive rounds with confirmed different pairings.

**Acceptance Scenarios**:

1. **Given** a coordinator with an existing team roster, **When** they follow the history how-to, **Then** they run two consecutive rounds and confirm the second round avoids repeating pairs from the first.
2. **Given** the history how-to, **When** a team member has left the team, **Then** the guide walks the coordinator through removing that person's entries from the history file using `--prune-history`.
3. **Given** the history how-to, **When** no history file exists yet, **Then** the guide explains that the file is created automatically on the first run with `--update-history`.

---

### User Story 3 - Coordinator Manages Absent Team Members (Priority: P2)

A coordinator needs to exclude members who are temporarily on leave without deleting them from the roster. They find a how-to guide that explains the `active` field, how to mark members as inactive, and how to reactivate them when they return.

**Why this priority**: Teams regularly have members on leave. Without this guide, coordinators either delete and re-add members (losing history and avoidance context) or leave absent members in the active pool (producing unusable pairings).

**Independent Test**: A coordinator follows the guide, marks a member as inactive, confirms a run excludes them, then reactivates the member and confirms the next run includes them.

**Acceptance Scenarios**:

1. **Given** a how-to guide on managing absences, **When** a coordinator sets `active: false` for a member, **Then** subsequent pairings exclude that member and the guide confirms expected output.
2. **Given** the same guide, **When** the absent member returns and the coordinator restores `active: true`, **Then** the member is included in the next pairing run.

---

### User Story 4 - Coordinator Prevents Specific Pairings (Priority: P2)

Certain pairs must never form — for example, a manager must not be paired with their direct report, since they already meet regularly. A coordinator finds a how-to guide explaining the `avoid_buddies` field, with the manager/report relationship as the primary concrete example. The guide also covers what happens when avoidance constraints conflict.

**Why this priority**: Avoidance is a correctness requirement for many teams. Without documentation, coordinators may not know the feature exists, or may configure it incorrectly and not notice failures until they inspect the output.

**Independent Test**: A coordinator follows the guide, configures an avoidance constraint for one pair, and verifies that pair never appears in subsequent runs.

**Acceptance Scenarios**:

1. **Given** a how-to on avoidance constraints, **When** a coordinator adds an `avoid_buddies` entry for a manager and their direct report, **Then** the guide explains how to verify the constraint is active and the pair never appears in output.
2. **Given** the same guide, **When** avoidance constraints are so restrictive that no valid pairing exists, **Then** the guide explains the resulting error message and how to resolve the conflict by relaxing constraints.
3. **Given** the guide, **When** a name in `avoid_buddies` does not match any roster member, **Then** the tool exits with a user-friendly validation error identifying the unrecognised name, and the guide explains this error and how to correct it.

---

### User Story 5 - Documentation Examples Stay Correct as the Tool Evolves (Priority: P2)

A developer changes the tool — for example, renames an option, adds a required field, or changes the output structure — and runs the test suite. Any documentation example that no longer matches the tool's actual behavior appears as a distinct test failure, identifying which example is broken and why. No manual documentation audit is needed to detect the regression.

**Why this priority**: Documentation that silently drifts from reality is worse than no documentation. Automated example testing is what makes the docs a reliable long-term asset rather than a snapshot that becomes stale. It is P2 because it directly protects the value of all other documentation stories.

**Independent Test**: Introduce a deliberate breaking change to the tool (e.g., rename `--team` to `--roster`) and run the test suite without updating the docs. At least one test must fail with a message that identifies the broken example.

**Acceptance Scenarios**:

1. **Given** the test suite, **When** all documented examples match the current tool behaviour, **Then** all example tests pass.
2. **Given** a CLI option is renamed or removed, **When** the docs still reference the old name and the test suite is run, **Then** a test fails and the failure message identifies which document and example is affected.
3. **Given** a required `team.yaml` field is added or renamed, **When** the docs still show the old file structure and the test suite is run, **Then** a test fails identifying the broken roster example.
4. **Given** the JSON output structure changes (e.g., a field is renamed), **When** the docs still document the old field name and the test suite is run, **Then** a test fails identifying the broken output example.
5. **Given** the test suite, **When** a developer runs it locally, **Then** the example tests are included automatically with no separate command needed.

---

### User Story 6 - User Looks Up a CLI Option (Priority: P3)

A user who already knows how to run the tool wants the precise behavior of a specific option — for example, what `--solver-profile adaptive` selects for a team of 20 people, or what happens if `--prune-history` is passed without `--update-history`. They find a CLI reference with complete, accurate descriptions of every option.

**Why this priority**: Reference documentation reduces support requests and eliminates trial-and-error usage of edge-case options. It is independent of the how-to guides and tutorial.

**Independent Test**: For any CLI option, the reference page answers: what it does, its default value, valid values or ranges, and any dependencies or interactions with other options — without the reader needing to look anywhere else.

**Acceptance Scenarios**:

1. **Given** the CLI reference, **When** a user looks up `--solver-profile`, **Then** they find descriptions of all four profiles (`fast`, `balanced`, `optimal`, `adaptive`), the team-size thresholds used by adaptive selection, and guidance on when to choose each.
2. **Given** the CLI reference, **When** a user looks up `--prune-history`, **Then** they see that it requires `--update-history` to have any effect, and the reference states explicitly what happens without it.
3. **Given** the CLI reference, **When** a user looks up `--history-weight` or `--tz-weight`, **Then** they see the default value, valid range (≥ 0.0), and how setting either to `0.0` disables that penalty entirely.
4. **Given** the CLI reference, **When** a user looks up `--history`, **Then** they see the default behavior (auto-infer path from team file name when `--update-history` is active, otherwise no history is loaded).

---

### User Story 7 - User Understands How the Algorithm Works (Priority: P4)

A user who wants to understand why the tool produces a particular pairing reads the explanation document. They learn what the objective function minimises, what the hard constraints are, how timezone similarity is assessed from label strings, how solver profiles trade solution quality for speed, and why avoidance constraints are never relaxed.

**Why this priority**: Understanding the algorithm builds confidence in the tool's outputs and enables users to tune weights intentionally. It does not block any practical use of the tool and is therefore lowest priority.

**Independent Test**: After reading the explanation, a user can answer the following without consulting source code: what does raising `--history-weight` do to the pairings, why might two timezone-mismatched members still be paired, what does "gap tolerance" mean for solution quality.

**Acceptance Scenarios**:

1. **Given** the explanation, **When** a user reads about the objective function, **Then** they understand the tool selects pairings that minimise a weighted sum of historical pairing frequency and timezone mismatch for each candidate pair.
2. **Given** the explanation, **When** a user reads about hard constraints, **Then** they understand that avoidance pairs and the coverage constraint (each member in exactly one pair) are absolute and never violated regardless of the penalty scores.
3. **Given** the explanation, **When** a user reads about solver profiles, **Then** they understand the tradeoff: a wider gap tolerance finishes faster but may not find the mathematically best assignment; a tighter tolerance takes longer but guarantees closer-to-optimal results.
4. **Given** the explanation, **When** a user reads about timezone scoring, **Then** they understand that similarity is measured by comparing the text of timezone labels — identical labels score zero penalty, completely different labels score maximum penalty — and they understand the implication for choosing consistent label formats.

---

### Edge Cases

- What if the user follows the tutorial but their platform does not support snap? The tutorial must present both installation paths as independent alternatives, each complete on its own.
- What if the roster grows far beyond the tutorial example? Documentation must note that the file format is identical for any team size and link to the reference for large-team solver profile guidance.
- What if a name in `avoid_buddies` is misspelled? The tool MUST exit with a validation error identifying the unrecognised name; the avoidance how-to must document this error and how to fix it.
- What if a user reads only the CLI reference without the tutorial? Each reference entry must include at least one concrete invocation example so the reference is usable standalone.
- What if the user passes `--prune-history` without `--update-history`? Both the CLI reference and the history how-to must document that the flag has no effect in that case and that a warning is emitted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The documentation MUST include a tutorial that guides a new user through installation, creating a team roster file, and generating their first pairing result via a dry run.
- **FR-002**: The tutorial MUST cover both installation methods: as a Python package via `uv tool install buddy-scheduler` and as a snap package, as independent paths.
- **FR-003**: The documentation MUST include a how-to guide for enabling and carrying forward pairing history across multiple rounds, covering `--update-history`, the auto-inferred history file path, and `--prune-history`.
- **FR-004**: The documentation MUST include a how-to guide for marking team members as temporarily inactive and reactivating them, using the `active` field in the roster file.
- **FR-005**: The documentation MUST include a how-to guide for configuring avoidance constraints using the `avoid_buddies` field, with the manager/direct-report relationship as the primary worked example. The guide MUST document that referencing an unrecognised name in `avoid_buddies` causes a validation error and must explain how to diagnose and correct it.
- **FR-006**: The documentation MUST include a CLI reference listing every option with its name, type, default value, accepted values or range, description of behaviour, and any interactions with other options.
- **FR-007**: The CLI reference MUST cover all eight current options: `--team`, `--history`, `--update-history`, `--prune-history`, `--history-weight`, `--tz-weight`, `--solver-profile`, and `--log-level`.
- **FR-008**: The documentation MUST include a reference for the `team.yaml` roster file format, covering all four fields: `name`, `timezone`, `active`, and `avoid_buddies`, with types, defaults, and constraints.
- **FR-009**: The documentation MUST include a reference for the JSON output format, covering all fields present in success and failure responses, including `pairs`, `sitting_out`, `optimization_score`, `solver_profile`, `history_updated`, `inactive_members`, `avoidance_conflicts`, and `error`.
- **FR-010**: The documentation MUST include a reference for exit codes, specifying the condition that triggers each code: 0 (success), 1 (validation error or infeasibility), and 2 (solver failure).
- **FR-011**: The documentation MUST include an explanation document describing the MIP objective function: a weighted sum of historical pairing frequency and timezone incompatibility, minimised over all candidate pairings, subject to coverage and avoidance hard constraints. The explanation MUST use narrative and formula descriptions only; numeric worked examples are out of scope.
- **FR-012**: The explanation MUST describe how timezone compatibility is measured — string similarity between timezone label text — including the practical implication that consistent label formatting improves grouping quality.
- **FR-013**: The explanation MUST describe sit-out fairness: when the team has an odd number of active members, the member who has sat out least often in recorded history is preferred for sit-out.
- **FR-014**: The explanation MUST describe solver profiles: what gap tolerance and time limit mean, the four profiles (fast, balanced, optimal, adaptive), and the team-size thresholds used by adaptive selection.
- **FR-015**: All four Diataxis document types (tutorial, how-to, reference, explanation) MUST be organised as clearly separated sections or files — no how-to instructions inside reference pages, no tutorial steps inside explanations.
- **FR-016**: Every command invocation in the documentation MUST use the exact option names and field names as they exist in the current implementation.
- **FR-017**: The documentation MUST include at least one complete, runnable example team roster file that demonstrates all four fields (`name`, `timezone`, `active`, `avoid_buddies`).
- **FR-018**: Every CLI command invocation and every `team.yaml` example in the documentation MUST be covered by an automated test in the project's test suite. Each test MUST execute the actual command (or validate the file against the actual validator), assert the expected exit code, and verify that every field documented for that command is present in the actual output (structural field-presence check; field values are not asserted, as they vary across runs). Tests MUST fail with a message identifying the specific document and example that is broken. These tests MUST run as part of the default test suite invocation with no additional command required.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time user with no prior knowledge can follow the tutorial and generate a valid pairing result within 15 minutes.
- **SC-002**: Every CLI option is covered in the reference with name, default, accepted values, and at least one example — 100% coverage of the 8 current options.
- **SC-003**: Each how-to guide covers exactly one task and can be completed independently of the other guides, with no prerequisite beyond completing the tutorial.
- **SC-004**: After reading the MIP explanation, a user can correctly predict the direction of change for both `--history-weight` and `--tz-weight` adjustments without consulting source code.
- **SC-005**: All command invocations and file examples in the documentation are covered by automated tests; every such test passes against the current version of the tool, and a breaking change to the tool causes at least one test to fail with an identifiable error.
- **SC-006**: The four Diataxis document types are clearly separated — a reviewer can classify every sentence in the documentation as belonging to exactly one type without ambiguity.

## Clarifications

### Session 2026-02-26

- Q: Which Python package install command should the tutorial show? → A: `uv tool install buddy-scheduler` (matches project toolchain; uv is already the project's package manager).
- Q: How should FR-018 tests verify output structure? → A: Structural field-presence check — assert that every field documented for a given command is present in the actual output; do not assert field values, which vary across runs.
- Q: Should the MIP explanation include a concrete numeric worked example? → A: No — narrative and formula only; no numeric values or sample tables.

## Assumptions

- Documentation will be delivered as Markdown files in a `docs/` directory within the repository, organised by Diataxis type (e.g., `docs/tutorial/`, `docs/how-to/`, `docs/reference/`, `docs/explanation/`).
- The primary audience is team coordinators who are comfortable running terminal commands but are not expected to have programming knowledge.
- The documentation targets Linux as the primary platform. Snap installation is Linux-only; the Python package path covers other platforms implicitly.
- Windows-specific installation steps are out of scope for this feature.
- The `examples/team.yaml` file in the repository may be referenced from documentation but is not a substitute for inline examples within the docs themselves.
- Documentation covers the tool at its current version (0.1.0); API-stability guarantees and versioning of the docs themselves are out of scope.
- The documentation accurately reflects desired tool behavior. Where desired behavior differs from the current implementation (e.g., `avoid_buddies` referencing an unknown name must produce a validation error, not be silently ignored), a corresponding implementation fix is a prerequisite for this documentation feature.
- The history file's internal JSON structure does not need to be documented beyond what a coordinator needs for day-to-day operation (i.e., they need to know the file exists and what `--prune-history` does, not the exact schema).
