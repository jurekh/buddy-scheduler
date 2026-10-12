# Contract: CLI Interface

**Tool**: `buddy-scheduler`
**Entry point**: `buddy_scheduler.cli:main`

## Invocation

```
buddy-scheduler --team TEAM_FILE [OPTIONS]
```

## Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `--team PATH` | file path | Yes | — | Path to the YAML team roster file |
| `--history PATH` | file path | No | — | Path to the JSON history store file |
| `--update-history` | flag | No | off | Persist new pairings to the history store after a successful run |
| `--prune-history` | flag | No | off | Remove stale entries (members absent from current roster) from the history store. Only valid with `--update-history` |
| `--history-weight FLOAT` | float ≥ 0.0 | No | 1.0 | Multiplier for the history repeat penalty |
| `--tz-weight FLOAT` | float ≥ 0.0 | No | 1.0 | Multiplier for the timezone incompatibility penalty |
| `--solver-profile CHOICE` | enum | No | adaptive | MIP solver settings profile: `fast`, `balanced`, `optimal`, `adaptive` |
| `--log-level CHOICE` | enum | No | INFO | Log verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## Rules

- `--prune-history` without `--update-history` MUST produce a validation error.
- `--history-weight` and `--tz-weight` MUST each be ≥ 0.0; negative values MUST
  produce a validation error.
- If `--history` is omitted but `--update-history` is supplied, the tool MUST
  create a new history store at the path implied by the team file name
  (e.g., `team.yaml` → `team_history.json`).

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Run completed successfully (pairings produced, including fallback results) |
| 1 | Run failed: validation error or infeasible avoidance constraints |
| 2 | Run failed: all fallback strategies exhausted (solver failure, not infeasibility) |

## Output contract

- All structured output (success or failure) MUST be written as a single JSON
  object to **stdout**.
- All log messages MUST be written to **stderr**.
- stdout and stderr MUST NOT be mixed.
