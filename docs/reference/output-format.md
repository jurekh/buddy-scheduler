# Output Format Reference

buddy-scheduler writes a single JSON document to stdout on every execution path, including failures. All diagnostic messages go to stderr.

---

## Success Response

A successful run produces exit code `0` and a JSON document with the following fields.

### Always-present fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Always `true` for a successful run |
| `pairs` | array of [string, string] | Pairs produced for this round. Each pair is a two-element array of member names, sorted alphabetically within the pair. The outer array is also sorted. |
| `sitting_out` | string or null | Name of the member sitting out this round (only when the active team has an odd number of members); `null` otherwise |
| `optimization_score` | number | Total penalty score minimised by the solver. `0.0` means no history penalty and no timezone mismatch penalty accumulated by the chosen pairs. Lower is better. |
| `solve_time` | number | Elapsed wall-clock time in seconds taken by the MIP solver |
| `solver_profile` | string | The resolved solver profile used: `"fast"`, `"balanced"`, or `"optimal"`. When `--solver-profile adaptive` is used, this shows the profile that was selected for the active team size. |
| `history_updated` | boolean | `true` if the history file was written during this run; `false` if this was a dry run |

### Conditional fields (present only when applicable)

| Field | Type | Condition |
|-------|------|-----------|
| `peak_memory_mb` | number | RSS memory of the buddy-scheduler process in megabytes, measured after the solve. Present whenever the solver ran (success or infeasible). |
| `memory_delta_mb` | number | Change in RSS memory in megabytes across the solve. Present whenever the solver ran. |
| `inactive_members` | array of strings | Names of members excluded because `active: false` in the roster. Present only when at least one inactive member exists. |
| `avoidance_conflicts` | array of strings | Descriptions of members with no eligible pairing partners due to avoidance constraints. Present only on an infeasible run where at least one member has no eligible partner left; an infeasible run without such a member omits this field. |

### Running a success example

<!-- test: cli fixture=minimal.yaml exit=0 -->
```bash
buddy-scheduler --team team.yaml
```

### Success example

```json
{
  "success": true,
  "pairs": [
    ["Alice", "Bob"],
    ["Charlie", "Diana"]
  ],
  "sitting_out": null,
  "optimization_score": 0.0,
  "solve_time": 0.042,
  "solver_profile": "optimal",
  "history_updated": false,
  "peak_memory_mb": 35.9,
  "memory_delta_mb": 0.02
}
```

### Success example with inactive member and history

```json
{
  "success": true,
  "pairs": [
    ["Alice", "Charlie"],
    ["Bob", "Diana"]
  ],
  "sitting_out": null,
  "optimization_score": 2.5,
  "solve_time": 0.055,
  "solver_profile": "optimal",
  "history_updated": true,
  "peak_memory_mb": 36.1,
  "memory_delta_mb": 0.02,
  "inactive_members": ["Frank"]
}
```

---

## Failure Response

A failed run produces exit code `1` or `2` (see below) and a JSON document with the following fields.

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Always `false` |
| `error` | string | Human-readable description of the failure |

Additional fields from the success schema (`pairs`, `sitting_out`, etc.) may also be present with default/empty values depending on how far execution progressed before the failure.

### Running a validation failure example

<!-- test: cli fixture=unknown-avoid-buddy.yaml exit=1 -->
```bash
buddy-scheduler --team team.yaml
```

### Failure example - validation error

```json
{
  "success": false,
  "error": "Member 'Alice' has unrecognised avoid_buddies entry 'Alic' — no member named 'Alic' exists in the roster"
}
```

### Failure example - fewer than 2 active members

```json
{
  "success": false,
  "pairs": [],
  "sitting_out": null,
  "optimization_score": 0.0,
  "solve_time": 0.0,
  "solver_profile": "optimal",
  "history_updated": false,
  "inactive_members": ["Bob"],
  "error": "Fewer than 2 active members; pairing is not possible."
}
```

### Failure example - infeasible constraints

```json
{
  "success": false,
  "pairs": [],
  "sitting_out": null,
  "optimization_score": 0.0,
  "solve_time": 0.011,
  "solver_profile": "optimal",
  "history_updated": false,
  "peak_memory_mb": 35.8,
  "memory_delta_mb": 0.02,
  "avoidance_conflicts": [
    "Alice has no eligible pairing partners"
  ],
  "error": "Infeasible: avoidance constraints prevent a valid pairing."
}
```

---

## Exit Codes

| Code | Condition |
|------|-----------|
| `0` | Successful run - pairs produced and emitted |
| `1` | Input validation failure (bad file, invalid field, unrecognised name in `avoid_buddies`), fewer than 2 active members, or infeasible avoidance constraints |
| `2` | MIP solver failure (non-optimal solver status not caused by infeasible constraints) |

On exit code `1` or `2`, the JSON document on stdout always contains `"success": false` and an `"error"` field describing the problem.

---

## Related References

- **CLI options**: [cli.md](cli.md)
- **team.yaml format**: [team-yaml.md](team-yaml.md)
