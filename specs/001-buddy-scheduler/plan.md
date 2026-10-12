# Implementation Plan: buddy-scheduler

**Branch**: `001-buddy-scheduler` | **Date**: 2026-02-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-buddy-scheduler/spec.md`

## Summary

Rewrite of the buddy-scheduler CLI tool: generates optimal team buddy pairings using
Mixed Integer Programming (PuLP/CBC). Inputs are a YAML team roster and an optional
JSON history store. Output is a JSON document on stdout. Core objectives are
minimising timezone incompatibility and pairing repetition via configurable penalty
weights, with hard avoidance constraints and inactive-member filtering. The ADAPTIVE
solver profile is the default; fallback strategies (greedy → random → round-robin)
handle solver failures. Test coverage ≥ 80% required; history writes are atomic.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: PuLP ≥ 2.7 (MIP/CBC), Click ≥ 8.1, PyYAML ≥ 6.0, psutil ≥ 5.9
**Storage**: Files — YAML team roster (human-authored), JSON history store (machine-managed)
**Testing**: pytest ≥ 8, pytest-cov ≥ 6, mypy ≥ 1.0 (strict), ruff ≥ 0.4
**Target Platform**: Linux (primary), macOS (secondary); distributed as pip package + snap
**Project Type**: CLI tool
**Performance Goals**: ≤ 5 seconds for 100 active members under the default (adaptive) profile
**Constraints**: No network access, no database, no daemon mode; offline-only; snap strict confinement
**Scale/Scope**: 2–100 active members; single team per invocation

## Constitution Check

*GATE: Must pass before implementation. Re-checked after Phase 1 design.*

### I. Type Safety & Validated Inputs ✅

- mypy strict mode configured; all modules fully annotated.
- Input validation occurs at the system boundary before any computation:
  - YAML team roster validated on load (required fields, unique names, type checks).
  - JSON history store validated on load (structure, symmetry, non-negative counts).
  - CLI parameter constraints enforced by Click (types, ranges, mutual dependencies).
- Exception hierarchy defined: `BuddySchedulerError → FileLoadError | FileSaveError |
  DataValidationError | OptimizationError`. No bare exceptions permitted.
- PuLP lacks type stubs; suppressed via `[[tool.mypy.overrides]]` with justification.

### II. Data Integrity ✅

- History JSON writes are atomic: write to temp file in same directory → `fsync` →
  `os.replace` (atomic rename).
- Existing history file backed up to `<path>.backup` before every overwrite.
- Concurrent write access serialised with `fcntl.lockf(LOCK_EX)`.
- Loaded history validated for symmetry and non-negative counts before use.

### III. Comprehensive Testing ✅

- Coverage gate: ≥ 80%, enforced in `make test` via `--cov-fail-under=80`.
- Unit tests for all non-trivial logic (models, io, optimizer, fallback, penalties,
  solver profile selection).
- Integration tests: full CLI pipeline with real YAML/JSON files via Click's
  `CliRunner`.
- Edge-case tests: empty team, one active member, odd team, infeasible constraints,
  corrupted history, partial writes.
- Benchmark tests gated behind `@pytest.mark.benchmark`; excluded from default run.
- Fallback and error paths explicitly tested (not only the happy path).

### IV. Transparent Operations ✅

- All structured results emitted as JSON to stdout.
- All diagnostic and log output emitted to stderr.
- Configurable log level (DEBUG / INFO / WARNING / ERROR), default INFO.
- Log coverage: input loading, validation, optimisation start/end, fallback
  activations, history reads/writes, errors.
- Duration (`solve_time`) and peak memory (`peak_memory_mb`, `memory_delta_mb`)
  logged at INFO and included in the JSON result.
- Component logger hierarchy: `buddy_scheduler.cli`, `buddy_scheduler.io`,
  `buddy_scheduler.optimizer`, `buddy_scheduler.fallback`, `buddy_scheduler.solver`.

### V. Graceful Degradation ✅

- ADAPTIVE solver profile is the default; auto-selects OPTIMAL / BALANCED / FAST
  based on active team size.
- Infeasibility from avoidance constraints detected before the MIP solve and reported
  immediately without attempting fallback.
- Fallback chain on solver exception or non-optimal non-infeasible status:
  `greedy_min_penalty → random_pairing → round_robin`.
- Fallback result flagged in output via `solver_profile` field encoding.

### Code Quality Standards ✅

- Python 3.11+ pinned in `pyproject.toml`; `uv.lock` committed.
- ruff rules: `E, F, W, I, B, UP, N, A, C4, RET, SIM`; line-length 88.
- mypy strict mode; PuLP missing-import suppression documented in config.
- isort enforced by ruff (rule `I`); no wildcard imports.
- Docstrings required on all public functions and classes.

### Development Workflow ✅

- All operations via `make <target>`: `setup`, `test`, `test-coverage`, `lint`,
  `typecheck`, `benchmark`, `build`, `clean`.
- `make lint` (ruff + mypy) passes before any commit.
- `make test` enforces coverage ≥ 80% before merge.
- `uv.lock` updated in same commit as any dependency change.
- `make build` produces an installable wheel; snap artefact via `make snap`.

## Project Structure

### Documentation (this feature)

```text
specs/001-buddy-scheduler/
├── plan.md              # This file
├── research.md          # Technology and architecture decisions
├── data-model.md        # Entities, MIP formulation, exception hierarchy
├── quickstart.md        # Operator usage guide
├── contracts/
│   ├── cli.md                    # CLI parameter contract
│   ├── team-roster-schema.yaml   # Input YAML schema + example
│   ├── history-store-schema.json # History JSON schema + example
│   └── result-schema.json        # Output JSON schema + examples
└── tasks.md             # Generated by /speckit.tasks
```

### Source Code (repository root)

```text
src/
└── buddy_scheduler/
    ├── __init__.py          # Package version constant
    ├── cli.py               # Click entry point; JSON serialisation; exit codes
    ├── models.py            # TeamMember, PairingHistory, OptimizationResult,
    │                        #   SolverProfile, exception hierarchy
    ├── io.py                # YAML roster loading; JSON history load/save;
    │                        #   atomic writes; file locking; backup
    ├── optimizer.py         # BuddyOptimizer: MIP formulation, constraint
    │                        #   generation, infeasibility detection
    ├── fallback.py          # greedy_min_penalty, random_pairing, round_robin
    ├── penalties.py         # history_penalty, timezone_penalty, sit_out_penalty
    └── solver.py            # SolverProfile → CBC config mapping;
                             #   ADAPTIVE resolution by team size

tests/
├── integration/
│   ├── test_cli.py              # Full pipeline via Click CliRunner
│   └── test_history_pipeline.py # update-history + prune-history flows
├── unit/
│   ├── test_models.py           # Dataclass validation, exception hierarchy
│   ├── test_io.py               # YAML loading, JSON load/save, atomic write,
│   │                            #   locking, backup, validation errors
│   ├── test_optimizer.py        # MIP formulation, constraint generation,
│   │                            #   infeasibility detection
│   ├── test_fallback.py         # Each fallback strategy independently
│   ├── test_penalties.py        # Penalty calculation functions
│   └── test_solver.py           # Profile→config mapping, ADAPTIVE thresholds
└── benchmarks/
    └── test_performance.py      # @pytest.mark.benchmark; 10/50/100 member teams

pyproject.toml      # Project metadata, dependencies, tool config
Makefile            # Development automation
uv.lock             # Pinned dependency tree
snapcraft.yaml      # Snap package definition
```

**Structure Decision**: Single `src/` layout with six focused modules. The `src/`
directory prevents import shadowing during testing. Six modules map directly to the
six component loggers required by Constitution Principle IV and keep each concern
independently unit-testable. No sub-packages are introduced; the codebase is not
large enough to warrant further nesting.

## Complexity Tracking

> No constitution violations. Table left empty.
