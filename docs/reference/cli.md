# CLI Reference

Command: `buddy-scheduler [OPTIONS]`

Entry point: `buddy_scheduler.cli:main`

---

## Options

| Option | Type | Required | Default | Valid values |
|--------|------|----------|---------|--------------|
| `--team PATH` | path | **yes** | — | Any readable file path |
| `--history PATH` | path | no | — | Any file path |
| `--update-history` | flag | no | `false` | — |
| `--prune-history` | flag | no | `false` | — |
| `--history-weight FLOAT` | float | no | `1.0` | ≥ 0.0 |
| `--tz-weight FLOAT` | float | no | `0.5` | ≥ 0.0 |
| `--solver-profile TEXT` | string | no | `adaptive` | `fast`, `balanced`, `optimal`, `adaptive` |
| `--log-level TEXT` | string | no | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Option Details

### `--team PATH`

Path to the YAML team roster file. This option is required on every invocation.

<!-- test: cli fixture=minimal.yaml exit=0 -->
```bash
buddy-scheduler --team team.yaml
```

```bash
buddy-scheduler --team /path/to/my-team.yaml
```

---

### `--history PATH`

Path to the JSON history store file. When supplied, the tool reads prior pairing counts from this file and uses them to penalise repeated pairs.

If `--update-history` is active and `--history` is not supplied, the history path is inferred automatically from the team file name: `<team-stem>.history.json` in the same directory. For example, `team.yaml` → `team.history.json`.

If neither `--history` nor `--update-history` is supplied, no history is loaded and no history is written (dry run).

```bash
buddy-scheduler --team team.yaml --history team.history.json
```

---

### `--update-history`

Persist the pairings from this run to the history store after a successful solve. If the history file does not exist, it is created automatically.

```bash
buddy-scheduler --team team.yaml --update-history
buddy-scheduler --team team.yaml --history /shared/history.json --update-history
```

---

### `--prune-history`

When writing the history file, remove entries for members who are not currently in the roster. Requires `--update-history` to have any effect. Without `--update-history`, the flag is ignored and a `WARNING` is emitted to stderr.

```bash
buddy-scheduler --team team.yaml --update-history --prune-history
```

---

### `--history-weight FLOAT`

Weight applied to the history repetition penalty in the objective function. A higher value makes the solver try harder to avoid recently repeated pairs. Setting to `0.0` disables the history penalty entirely (pairings are chosen based on timezone compatibility only).

Default: `1.0` | Valid range: ≥ 0.0 | Negative values are a validation error (exit 1).

```bash
buddy-scheduler --team team.yaml --history-weight 2.0
buddy-scheduler --team team.yaml --history-weight 0.0   # ignore history
```

Negative values produce a validation error (exit code 1):

<!-- test: cli fixture=minimal.yaml exit=1 -->
```bash
buddy-scheduler --team team.yaml --history-weight -1.0
```

---

### `--tz-weight FLOAT`

Weight applied to the timezone incompatibility penalty in the objective function. A higher value makes the solver prefer to pair members in similar timezones. Setting to `0.0` disables timezone scoring entirely (pairings are chosen based on history only).

Default: `0.5` | Valid range: ≥ 0.0 | Negative values are a validation error (exit 1).

```bash
buddy-scheduler --team team.yaml --tz-weight 0.5
buddy-scheduler --team team.yaml --tz-weight 0.0   # ignore timezones
```

Negative values produce a validation error (exit code 1):

<!-- test: cli fixture=minimal.yaml exit=1 -->
```bash
buddy-scheduler --team team.yaml --tz-weight -0.1
```

---

### `--solver-profile TEXT`

Controls the MIP solver's gap tolerance and time limit. Case-insensitive.

| Profile | Gap tolerance | Time limit | When to use |
|---------|--------------|------------|-------------|
| `fast` | 20% | 10 s | Very large teams (> 60 members) where solve speed matters more than optimality |
| `balanced` | 1% | 60 s | Mid-size teams (16–60 members); good tradeoff of speed and quality |
| `optimal` | 0.1% | 300 s | Small teams (≤ 15 members) where the best possible assignment is desired |
| `adaptive` | (automatic) | (automatic) | **Default.** Selects a profile based on team size: N ≤ 15 → `optimal`, 16–60 → `balanced`, N > 60 → `fast` |

The `solver_profile` field in the output always shows the resolved profile name (e.g., `"optimal"` when `adaptive` selects `optimal` for a small team).

```bash
buddy-scheduler --team team.yaml --solver-profile optimal
buddy-scheduler --team team.yaml --solver-profile fast
```

An unrecognised profile name produces a validation error (exit code 1):

<!-- test: cli fixture=minimal.yaml exit=1 -->
```bash
buddy-scheduler --team team.yaml --solver-profile bogus
```

---

### `--log-level TEXT`

Sets the verbosity of diagnostic messages written to stderr. Case-insensitive.

| Level | What is shown |
|-------|---------------|
| `DEBUG` | All messages, including internal solver details |
| `INFO` | Normal operational messages (file loads, solve start/end, history read/write) |
| `WARNING` | Warnings only (e.g., `--prune-history` without `--update-history`) |
| `ERROR` | Errors only |

Default: `INFO` | An unrecognised level is a validation error (exit 1).

```bash
buddy-scheduler --team team.yaml --log-level DEBUG
buddy-scheduler --team team.yaml --log-level WARNING
```

An unrecognised level produces a validation error (exit code 1):

<!-- test: cli fixture=minimal.yaml exit=1 -->
```bash
buddy-scheduler --team team.yaml --log-level VERBOSE
```

---

## Standard Streams

| Stream | Content |
|--------|---------|
| `stdout` | JSON result document — always present on every execution path, including failure |
| `stderr` | Log messages and diagnostic output only |

---

## Exit Codes

| Code | Condition |
|------|-----------|
| `0` | Successful run — pairs produced and emitted |
| `1` | Input validation failure or infeasible avoidance constraints |
| `2` | MIP solver failure |

---

## Invocation Examples

```bash
# Basic dry run (no history)
buddy-scheduler --team team.yaml

# Run with automatic history tracking
buddy-scheduler --team team.yaml --update-history

# Run with explicit history file path
buddy-scheduler --team team.yaml --history /shared/history.json --update-history

# Prune departed members and update history
buddy-scheduler --team team.yaml --update-history --prune-history

# Adjust weights: prioritise history over timezone
buddy-scheduler --team team.yaml --history team.history.json \
  --history-weight 3.0 --tz-weight 0.5 --update-history

# Use a specific solver profile with debug logging
buddy-scheduler --team team.yaml --solver-profile optimal --log-level DEBUG

# Extract just the pairs with jq
buddy-scheduler --team team.yaml | jq '.pairs'
```

---

## Related References

- **team.yaml format**: [team-yaml.md](team-yaml.md)
- **Output JSON format and exit codes**: [output-format.md](output-format.md)
