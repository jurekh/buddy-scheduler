# CLI Contract: buddy-scheduler

**Date**: 2026-02-26 | **Branch**: `001-buddy-scheduler`

Entry point: `buddy_scheduler.cli:main` (declared in `[project.scripts]`).

---

## Command

```
buddy-scheduler [OPTIONS]
```

---

## Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `--team PATH` | Path | Yes | — | Path to YAML team roster file |
| `--history PATH` | Path | No | — | Path to JSON history store file |
| `--update-history` | Flag | No | `false` | Persist new pairings to history store after run |
| `--prune-history` | Flag | No | `false` | Remove stale history entries on write (requires `--update-history`) |
| `--history-weight FLOAT` | float | No | `1.0` | Weight applied to history repetition penalty |
| `--tz-weight FLOAT` | float | No | `1.0` | Weight applied to timezone incompatibility penalty |
| `--solver-profile TEXT` | str | No | `adaptive` | Solver profile: `fast`, `balanced`, `optimal`, `adaptive` |
| `--log-level TEXT` | str | No | `INFO` | Log verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

**Constraints**:
- `--prune-history` without `--update-history` emits a WARNING to stderr and has no effect; it is not a validation error
- If `--history` is omitted and `--update-history` is active, history path is inferred as `<team-stem>.history.json` in the same directory as the team file (e.g. `team.yaml` → `team.history.json`)
- `--history-weight` and `--tz-weight` must be ≥ 0.0; negative values are a validation error (exit 1)
- `--solver-profile` is case-insensitive; an unknown value is a validation error (exit 1)
- `--log-level` is case-insensitive; an unknown value is a validation error (exit 1)

---

## Standard Streams

| Stream | Content |
|--------|---------|
| `stdout` | JSON result document — always present on every execution path, including failure |
| `stderr` | Structured log messages and diagnostic output only |

---

## Exit Codes

| Code | Condition |
|------|-----------|
| `0` | Successful run — pairs produced and emitted |
| `1` | Input validation failure or infeasible avoidance constraints |
| `2` | MIP solver failure (non-optimal status not caused by infeasible constraints) |

---

## Invocation Examples

```bash
# Basic run (no history)
buddy-scheduler --team team.yaml

# Run with history, update after success
buddy-scheduler --team team.yaml --history history.json --update-history

# Prune stale members from history on update
buddy-scheduler --team team.yaml --history history.json --update-history --prune-history

# Custom weights and profile
buddy-scheduler --team team.yaml --history history.json \
  --history-weight 2.0 --tz-weight 0.5 --solver-profile optimal

# Debug logging
buddy-scheduler --team team.yaml --log-level DEBUG

# Parse result with jq
buddy-scheduler --team team.yaml | jq '.pairs'
```

---

## Logging Contract (stderr)

Log lines follow the format: `YYYY-MM-DD HH:MM:SS,mmm [LEVEL] message`

| Operation | Level |
|-----------|-------|
| Input file load start / complete | INFO |
| Validation pass / fail | INFO / ERROR |
| Optimization start | INFO |
| Solver profile selected (resolved name for adaptive) | INFO |
| Optimization complete with gap and duration | INFO |
| History read / write | INFO |
| History prune | INFO |
| Run complete (total duration + peak memory) | INFO |
| `--prune-history` without `--update-history` | WARNING |
| Any error | ERROR |

---

## Related Contracts

- **Output JSON format**: `result-schema.json`
- **team.yaml format**: `team-roster-schema.yaml`
- **History store format**: `history-store-schema.json`
