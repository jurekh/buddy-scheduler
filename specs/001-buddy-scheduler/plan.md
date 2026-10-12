# Implementation Plan: buddy-scheduler

**Branch**: `001-buddy-scheduler` | **Date**: 2026-02-25 | **Spec**: `specs/001-buddy-scheduler/spec.md`
**Input**: Feature specification from `/specs/001-buddy-scheduler/spec.md`

## Summary

A CLI tool that generates optimised buddy pairings for a team using Mixed Integer
Programming (MIP). The tool reads a YAML team roster, optionally loads a JSON
history store, solves a weighted perfect-matching ILP with PuLP/CBC, emits a JSON
result to stdout, and optionally persists the new pairings back to the history store.
Fallback strategies (greedy, random, round-robin) activate only on solver failure —
not on infeasible constraints, which are reported and exited immediately.

## Technical Context

**Language/Version**: Python 3.11
**Package manager**: uv — `uv.lock` committed; `.python-version` pinned to `3.11`
**Primary Dependencies**: PuLP ≥ 2.7 (MIP/CBC), Click ≥ 8.1, PyYAML ≥ 6.0,
psutil ≥ 5.9, Pydantic ≥ 2.0 (JSON validation), py-filelock ≥ 3.12 (locking)
**Storage**: YAML (team roster, human-authored); JSON (history store, machine-managed)
**Testing**: pytest + pytest-cov; coverage ≥ 80%; `@pytest.mark.slow` gates
long-running or resource-intensive tests
**Target Platform**: Linux (primary); macOS compatible; py-filelock is cross-platform
**Project Type**: CLI tool
**Performance Goals**: Complete run for N ≤ 100 active members in < 5 s (SC-004)
**Constraints**: JSON output well-formed on all execution paths; peak memory suitable
for a CLI process
**Scale/Scope**: 2–100 active team members per run

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Type Safety & Validated Inputs — PASS

- All public interfaces typed; mypy runs in strict mode as a CI gate
- Input validation at system boundaries before optimization begins: YAML roster
  validated after `yaml.safe_load`; JSON history validated with Pydantic v2
- Typed exception hierarchy: `BuddySchedulerError` base; `FileLoadError`,
  `FileSaveError`, `DataValidationError`, `OptimizationError` subclasses

### II. Data Integrity — PASS

- History store writes are atomic: `tempfile.NamedTemporaryFile` + `os.fsync` +
  `os.replace`
- Backup: existing file moved to `<path>.backup` before overwrite
- File locking: `FileLock(f"{history_path}.lock")` (py-filelock) wraps all reads
  and writes to the history store
- All loaded state validated before use (Pydantic for JSON, custom checks for YAML)

### III. Comprehensive Testing — PASS

- ≥ 80% coverage enforced via `pytest-cov` as a make gate
- Unit tests for MIP formulation, fallback strategies, history I/O, validators,
  timezone utility
- Integration tests covering the full pipeline from YAML input to JSON output
- Edge-case tests: empty team, single member, odd N, infeasible constraints,
  corrupted history, stale history entries
- Slow/resource tests gated behind `@pytest.mark.slow`; excluded from default run

### IV. Transparent Operations — PASS

- JSON result (success and failure) always emitted to stdout
- All log output to stderr at configurable level (DEBUG/INFO/WARNING/ERROR),
  default INFO
- Logged at INFO: input load, validation, solve start/end, fallback activations,
  history I/O, total duration, peak memory (FR-018)

### V. Graceful Degradation — PASS

- Fallback chain: greedy → random → round-robin, activated only on solver failure
- Infeasibility (avoidance constraints) detected before fallback attempt, reported
  immediately with `avoidance_conflicts` detail (FR-011)
- Adaptive solver profile auto-selects settings based on team size (FR-008)

### Code Quality — PASS

- Python 3.11 pinned in `.python-version`; `uv.lock` committed;
  `requires-python = ">=3.11"` in `pyproject.toml`
- ruff for linting and formatting; no unresolved violations permitted in CI
- mypy strict mode; `pulp.*` override for missing stubs declared explicitly
- Import ordering enforced by ruff isort rules; wildcard imports not permitted
- Public functions and classes must have docstrings

### Development Workflow — PASS

- All operations expressible as `make <target>` using `uv run` internally
- Lint and typecheck pass before commit
- Tests run with ≥ 80% coverage before merge
- `uv add` + `uv.lock` update in same commit
- `make build` produces distributable wheel

**No violations. Complexity Tracking table not required.**

## Project Structure

### Documentation (this feature)

```text
specs/001-buddy-scheduler/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── cli-schema.md    # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks — not created here)
```

### Source Code

```text
src/
└── buddy_scheduler/
    ├── __init__.py
    ├── cli.py           # Click entry point; argument parsing; run orchestration
    ├── models.py        # TeamMember, PairingHistory, OptimizationResult; typed dataclasses; exception hierarchy
    ├── history.py       # PairingHistory I/O: load (Pydantic), save (atomic), update, prune
    ├── solver/
    │   ├── __init__.py
    │   ├── mip.py       # PuLP ILP formulation: variables, constraints, objective, solve
    │   ├── fallback.py  # Greedy, random, round-robin fallback strategies
    │   └── profiles.py  # SolverProfile enum; CBC option mapping; adaptive threshold logic
    ├── validator.py     # YAML roster validation; history pre-use checks
    └── tz_utils.py      # Timezone string similarity via difflib

tests/
├── contract/
│   └── test_cli_contract.py   # JSON output schema, exit codes, stdout/stderr routing
├── integration/
│   └── test_pipeline.py       # Full run: YAML → solve → JSON output, history persistence
└── unit/
    ├── test_mip.py             # ILP formulation correctness, constraint coverage, objective
    ├── test_fallback.py        # Greedy, random, round-robin correctness and avoidance honoring
    ├── test_history.py         # Atomic write, locking, prune, stale-entry handling
    ├── test_models.py          # Data model invariants (symmetry, non-negative counts)
    ├── test_validator.py       # Validation error paths for roster and history
    └── test_tz_utils.py        # Timezone similarity edge cases
```

**Structure Decision**: Single-project layout with `src/` package. Solver logic is
split into a `solver/` sub-package to isolate MIP formulation, fallback strategies,
and solver profile configuration as independently testable units. No frontend, no
backend split — this is a pure CLI tool.
