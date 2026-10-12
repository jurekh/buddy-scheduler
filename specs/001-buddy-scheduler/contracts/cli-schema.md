# CLI Contract: buddy-scheduler

**Phase**: 1 | **Date**: 2026-02-25 | **Branch**: `001-buddy-scheduler`

## Command

```
buddy-scheduler [OPTIONS]
```

Entry point: `buddy_scheduler.cli:main` (declared in `[project.scripts]`).

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
- `--prune-history` without `--update-history` is silently ignored with a WARNING log
- `--history-weight` and `--tz-weight` must be ≥ 0.0; negative values are a validation
  error (exit 1)
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
| `2` | Solver failure after all fallback strategies exhausted |

---

## JSON Output Schema

All output is a single JSON object. `success` is always present.

### Success

```json
{
  "success": true,
  "pairs": [["string", "string"]],
  "sitting_out": "string | null",
  "score": 0.0,
  "solver_profile": "string",
  "solver_gap": 0.0,
  "solve_duration_s": 0.0,
  "peak_memory_mb": 0.0,
  "inactive_members": ["string"],
  "avoidance_conflicts": null
}
```

| Field | Type | Notes |
|-------|------|-------|
| `pairs` | `list[list[str, str]]` | Each pair sorted lexicographically; outer list sorted |
| `sitting_out` | `str \| null` | Non-null only when active member count is odd |
| `score` | `float` | Weighted objective value; lower is better |
| `solver_profile` | `str` | MIP: `"{profile}"`; fallback: `"{profile}_fallback_{strategy}"` |
| `solver_gap` | `float \| null` | Achieved MIP optimality gap; `null` for fallback solutions |
| `solve_duration_s` | `float` | Seconds from solve start to end |
| `peak_memory_mb` | `float` | Peak process RSS in MB |
| `inactive_members` | `list[str]` | Sorted list of member IDs excluded due to `active: false` |
| `avoidance_conflicts` | `null` | Always `null` on success |

### Failure

```json
{
  "success": false,
  "error": "string",
  "avoidance_conflicts": [["string", "string"]] | null
}
```

| Field | Type | Notes |
|-------|------|-------|
| `error` | `str` | Human-readable, actionable error description |
| `avoidance_conflicts` | `list[list[str, str]] \| null` | Present only for infeasibility failures; `null` otherwise |

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

Log lines follow the format: `YYYY-MM-DD HH:MM:SS [LEVEL] message`

Significant operations logged at the indicated level:

| Operation | Level |
|-----------|-------|
| Input file load start / complete | INFO |
| Validation pass / fail | INFO / ERROR |
| Optimization start | INFO |
| Solver profile selected (and why, for adaptive) | INFO |
| Optimization complete (MIP) with gap and duration | INFO |
| Fallback activation (strategy name) | WARNING |
| Fallback complete | INFO |
| History read / write | INFO |
| History prune | INFO |
| Run complete (total duration + peak memory) | INFO |
| Any error | ERROR |

---

## Team Roster YAML Schema

```yaml
members:
  - name: string          # required; unique within roster
    timezone: string      # required; free-form
    active: boolean       # optional; default true
    avoid_buddies:        # optional; default []
      - string            # member name to never pair with
```

---

## History Store JSON Schema

Minimum valid empty store:

```json
{
  "version": "1",
  "pair_counts": {},
  "sit_out_counts": {}
}
```

See `data-model.md` for the full structure and invariants.
