# buddy-scheduler-speckit Development Guidelines

Last updated: 2026-10-12

## Active Technologies
- Python 3.11, managed with uv (`uv.lock` committed)
- Runtime: PuLP >= 2.7 (MIP/CBC), Click >= 8.1, PyYAML >= 6.0, psutil >= 5.9, Pydantic v2, filelock >= 3.12
- Dev: pytest >= 7.0, pytest-cov, hypothesis >= 6.0, ruff, mypy (strict)
- Data: YAML team roster (human-authored); JSON history store (machine-managed)
- Docs: Diataxis-structured Markdown in `docs/`; shared YAML fixtures in `tests/fixtures/`
- Packaging: hatchling (wheel/sdist); snapcraft, base core24, strict confinement

## Project Structure

```text
src/buddy_scheduler/   # cli, models, history, validator, tz_utils, solver/
tests/                 # unit, integration, contract, performance, fuzz
docs/                  # tutorial, how-to, reference, explanation
specs/                 # speckit feature specs (001-006)
snap/snapcraft.yaml
```

## Commands

```bash
make install     # uv sync --all-groups
make test        # fast tests, 80% coverage gate
make test-full   # includes slow (fuzz, performance) tests
make lint        # ruff check + ruff format --check
make format      # ruff format
make typecheck   # mypy strict
make build       # sdist + wheel
make snap        # snapcraft pack
make clean
```

## Code Style

Python 3.11+: ruff (line length 88) and mypy strict must pass.

## Recent Changes
- 006-fuzz-input-files: Added hypothesis >= 6.0 (dev dep); fuzz tests for input loaders
- 005-input-validation-tdd: Input validation tests and explicit path-kind guards
- 004-performance-fairness-tests: Timing, memory and fairness distribution tests
