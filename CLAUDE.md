# buddy-scheduler-speckit Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-24

## Active Technologies
- Python 3.11 + PuLP ≥ 2.7 (MIP/CBC), Click ≥ 8.1, PyYAML ≥ 6.0, (001-buddy-scheduler)
- YAML (team roster, human-authored); JSON (history store, machine-managed) (001-buddy-scheduler)
- Python 3.11 + Click ≥ 8.1 (CliRunner for doc tests), PyYAML ≥ 6.0, PuLP ≥ 2.7, psutil ≥ 5.9 — all existing; no new runtime deps (002-diataxis-docs)
- Markdown files in `docs/`; shared YAML fixtures in `tests/fixtures/` (002-diataxis-docs)
- Python 3.11 (unchanged); snapcraft 8.x; base: core24 + snapcraft Python plugin (built-in); no new runtime deps (003-snap-strict)
- N/A — packaging change only; existing file I/O is unchanged (003-snap-strict)

- Python 3.11+ + PuLP ≥ 2.7 (MIP/CBC), Click ≥ 8.1, PyYAML ≥ 6.0, psutil ≥ 5.9 (001-buddy-scheduler)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes
- 003-snap-strict: Added Python 3.11 (unchanged); snapcraft 8.x; base: core24 + snapcraft Python plugin (built-in); no new runtime deps
- 002-diataxis-docs: Added Python 3.11 + Click ≥ 8.1 (CliRunner for doc tests), PyYAML ≥ 6.0, PuLP ≥ 2.7, psutil ≥ 5.9 — all existing; no new runtime deps
- 002-diataxis-docs: Added Python 3.11 + Click ≥ 8.1 (CliRunner for doc tests), PyYAML ≥ 6.0, PuLP ≥ 2.7, psutil ≥ 5.9 — all existing; no new runtime deps


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
