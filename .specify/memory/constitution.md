<!--
  SYNC IMPACT REPORT
  Version change: 1.0.0 → 1.1.0 (MINOR — principles generalized from implementation
  details to architectural rules; no principles added or removed)
  Modified principles:
    I.  Type Safety — removed specific exception class names; made type-checker-agnostic
    II. Data Integrity — removed fcntl, .backup, history-specific invariants; generalized
    III. Testing — removed specific marker syntax and domain examples; kept coverage gate
    IV. Transparent Operations — removed specific metric names; generalized logger guidance
    V.  Graceful Degradation — removed MIP/solver/profile specifics; generalized to pattern
  Modified sections:
    Code Quality Standards — removed tool versions, specific rule sets, and engine-specific
    suppressions; kept as toolchain-class requirements
    Development Workflow — removed tool-specific targets; kept as workflow pattern
  Templates reviewed:
    ✅ .specify/templates/plan-template.md  — no updates required
    ✅ .specify/templates/spec-template.md  — no updates required
    ✅ .specify/templates/tasks-template.md — no updates required
  Deferred TODOs: None
-->

# buddy-scheduler Constitution

## Core Principles

### I. Type Safety & Validated Inputs

All public interfaces MUST declare explicit types enforced by a type checker running
in strict mode. Input validation MUST occur at system boundaries before any
computation begins. All domain errors MUST be raised through a typed exception
hierarchy; bare or untyped exceptions are not permitted.

**Rationale**: Strict typing and early validation catch entire classes of bugs at
analysis time. A typed exception hierarchy ensures errors surface with actionable
context rather than as opaque tracebacks.

### II. Data Integrity

Persistent state MUST be written atomically (write to a temporary location → sync →
rename into place). Existing state MUST be backed up before every destructive
overwrite. Concurrent write access MUST be guarded by a platform-appropriate locking
mechanism. All state loaded from external storage MUST be validated for internal
consistency before use.

**Rationale**: File-based state is the system's source of truth. Corrupt or partial
writes cannot be recovered automatically; prevention is cheaper than recovery.

### III. Comprehensive Testing

Test coverage MUST remain ≥ 80%. Every feature MUST include unit tests for
non-trivial logic, integration tests covering the full execution pipeline, and
edge-case tests for boundary and error conditions. Long-running or resource-intensive
tests MUST be gated behind a marker and excluded from the default test run. Tests
MUST exercise fallback and error paths, not only the happy path.

**Rationale**: High coverage ensures changes to complex logic are validated against
known-good baselines and regressions in error handling are caught before release.

### IV. Transparent Operations

Structured output MUST be written to stdout. Human-readable diagnostic output MUST
be written to stderr. All significant operations MUST be logged at an appropriate
level using a consistent logger hierarchy. Duration and resource-usage metrics MUST
be recorded at the end of each major operation.

**Rationale**: The tool runs unattended in automated pipelines. Operators need
sufficient signal in logs to diagnose failures without interactive access.

### V. Graceful Degradation

When primary computation fails, the system MUST attempt a pre-defined sequence of
fallback strategies rather than aborting. Inputs that cannot produce a valid result
MUST be detected and reported before computation begins. Configuration MUST adapt
automatically to workload characteristics where possible.

**Rationale**: Operations have time constraints. A lower-quality result delivered on
time is more useful than an optimal result that never arrives.

## Code Quality Standards

- The language version, package manager, and dependency manifest MUST be pinned
  explicitly and committed to the repository
- A linter and formatter MUST be configured with an explicit rule set; no unresolved
  violations are permitted in CI
- Complexity suppressions MUST be documented with a justification inline
- A type checker MUST run in strict mode; stubs for third-party dependencies MUST be
  declared as dev dependencies where available; suppression overrides require explicit
  justification
- Import ordering MUST be enforced by tooling; wildcard imports are not permitted
- Public functions and classes MUST have docstrings

## Development Workflow

- All development operations MUST be expressible as `make <target>` commands
- Linting and type-checking MUST pass before any commit
- Tests MUST pass with coverage ≥ 80% before merging
- Dependency changes MUST update the lock file in the same commit
- A distributable artefact MUST be buildable from a single make target before a
  release is tagged

## Governance

This constitution supersedes all other written or implicit engineering practices.
Any amendment MUST:

1. Update this file with a version bump per the semantic versioning policy below.
2. Include a rationale for the change in the Sync Impact Report comment block.
3. Be reflected in any affected templates under `.specify/templates/`.

**Versioning policy**:
- MAJOR: Removal or redefinition of an existing principle (backward-incompatible governance change)
- MINOR: New principle or section added; materially expanded or revised guidance
- PATCH: Clarification, wording refinement, typo fix

All pull requests and spec reviews MUST verify compliance with the Constitution Check
gate in the plan template before proceeding to implementation.

**Version**: 1.1.0 | **Ratified**: 2026-02-24 | **Last Amended**: 2026-02-24
