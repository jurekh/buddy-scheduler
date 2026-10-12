# Research: buddy-scheduler

**Branch**: `001-buddy-scheduler` | **Date**: 2026-02-24

## Decisions

### 1. Package Layout

**Decision**: `src/` layout — `src/buddy_scheduler/` package with separate modules per
concern.

**Rationale**: The `src/` layout prevents the local source directory from shadowing the
installed package during testing. Separate modules (cli, models, io, optimizer,
fallback, penalties, solver) keep each concern independently testable and directly
map to the constitution's logging hierarchy requirement (one logger per component).
The original single-file approach produced a 2400-line file that was difficult to
navigate and test in isolation; the rewrite should not repeat that.

**Alternatives considered**:
- Single module (`buddy_scheduler.py`): rejected — 2400 LOC is unwieldy; crossing
  component boundaries becomes invisible to the type checker and hard to test.
- `src/` with a single subpackage (`src/buddy_scheduler/optimization/`, etc.):
  rejected as over-engineering for the current size; can always add sub-packages
  later if the optimizer grows.

---

### 2. MIP Solver Library

**Decision**: PuLP with the bundled CBC solver.

**Rationale**: PuLP is the only mature, open-source Python MIP interface that ships
with CBC (COIN-OR Branch and Cut) out of the box with no separate installation.
The spec explicitly requires MIP. CBC is performant enough for ≤100 members.

**Alternatives considered**:
- OR-Tools (Google): heavier dependency (~200MB), more complex API; overkill for
  this problem size.
- Gurobi/CPLEX: commercial; excluded by open-source requirement.
- scipy.optimize.milp: MIP support added in SciPy 1.9 but API is lower-level and
  lacks CBC's out-of-box integration.

---

### 3. CLI Framework

**Decision**: Click 8.x.

**Rationale**: Click provides clean parameter validation, automatic `--help`
generation, and a testable `CliRunner` for integration tests. This maps directly
to the integration test requirement for the full CLI pipeline.

**Alternatives considered**:
- argparse (stdlib): more verbose, harder to test, no built-in type coercion.
- Typer: Click-based, but adds FastAPI-style annotations that add complexity without
  benefit for a simple single-command tool.

---

### 4. Package Manager and Distribution

**Decision**: `uv` with `pyproject.toml`; distributed as a pip-installable package
and snap.

**Rationale**: `uv` generates a lock file (`uv.lock`) and installs reproducibly.
The CLI entry point is declared as `[project.scripts]`:
```toml
[project.scripts]
buddy-scheduler = "buddy_scheduler.cli:main"
```
Snap packaging uses `base: core24`, `plugin: python`.

**Alternatives considered**:
- pip + requirements.txt: no lock file with hashes, non-reproducible.
- Poetry: heavier, slower than uv.

---

### 5. Linting and Type Checking

**Decision**: ruff (lint + format) + mypy strict.

**ruff rule set**:
```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "N", "A", "C4", "RET", "SIM"]
line-length = 88
```

**mypy** strict mode with PuLP override:
```toml
[tool.mypy]
strict = true

[[tool.mypy.overrides]]
module = "pulp.*"
ignore_missing_imports = true
```

**Alternatives considered**:
- flake8 + black: two tools instead of one; ruff supersedes both.
- pylint: slow, noisy, not worth the signal/noise tradeoff.

---

### 6. Testing

**Decision**: pytest + pytest-cov (≥80% gate) + benchmark exclusion via marker.

```toml
[tool.pytest.ini_options]
markers = ["benchmark: long-running performance tests"]
addopts = "-m 'not benchmark'"
```

Benchmark tests run via `make benchmark` (`pytest -m benchmark`).

---

### 7. File Locking

**Decision**: `fcntl.lockf()` (POSIX standard, preferred over `fcntl.flock()`).

Used exclusively around the atomic write sequence for the history JSON:
lock → read → write temp → rename → unlock.

---

### 8. Timezone Compatibility Scoring

**Decision**: String similarity via `difflib.SequenceMatcher` ratio, identical to
the original implementation.

**Rationale**: Timezone strings in practice follow patterns like "UTC+1", "America/New_York",
"Europe/London". Exact matching would fail across naming conventions; strict offset
arithmetic would require parsing all formats. String similarity is a pragmatic
approximation that requires no external dependency and performs well enough for
the use case.

**Alternatives considered**:
- pytz / zoneinfo offset comparison: requires standardised timezone names; fails
  on free-form strings like "BST+1" or "NYC".
- No timezone scoring (treat all as compatible): removes a key quality signal.
