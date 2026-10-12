# team.yaml Format Reference

The team roster file is a YAML file containing a list of member entries. Pass it to the tool with `--team`.

---

## File Structure

```yaml
- name: <string>
  timezone: <string>
  active: <boolean>          # optional, default: true
  avoid_buddies:             # optional, default: []
    - <string>
    - <string>
```

The file must be a YAML list. Each element is a mapping representing one team member.

---

## Fields

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `name` | string | **yes** | - | Non-empty; must be unique within the file |
| `timezone` | string | **yes** | - | Non-empty; free-form string (e.g. `"UTC+0"`, `"America/New_York"`, `"EMEA"`) |
| `active` | boolean | no | `true` | Must be a YAML boolean (`true` or `false`); strings like `"yes"` are a validation error |
| `avoid_buddies` | list of strings | no | `[]` | Each entry must exactly match the `name` of another member in the same file; unrecognised names are a validation error |

---

## Field Details

### `name`

A unique display name for the team member. Used in all output fields (`pairs`, `sitting_out`, `inactive_members`, `avoidance_conflicts`) and in `avoid_buddies` references.

Names are case-sensitive. `"Alice"` and `"alice"` are treated as different members.

---

### `timezone`

A free-form string describing where the member works. The tool uses string similarity between timezone labels to score timezone compatibility - it does not parse timezone names against any standard database.

**Implication for label consistency**: Members with identical timezone strings score zero timezone penalty with each other. Members with very different strings score high penalty. If your team uses inconsistent labels (e.g., `"UTC+1"` vs `"Europe/Paris"` for the same region), the tool may not recognise they are in the same timezone. Using consistent labels across all members in the same timezone improves pairing quality.

---

### `active`

Controls whether a member participates in the current pairing round.

- `active: true` (default) - member is included in pairing
- `active: false` - member is excluded; they appear in `inactive_members` in the output

Marking a member inactive does not remove their history. When they return, prior pairing data is still used.

---

### `avoid_buddies`

A list of member names that this member should never be paired with. The constraint is symmetric - listing `Bob` under Alice's `avoid_buddies` also prevents Bob from being paired with Alice, even if Bob's entry does not mention Alice.

Every name in `avoid_buddies` must exactly match the `name` field of another member in the file. An unrecognised name causes the tool to exit with a validation error (exit code 1) before attempting to solve.

Avoidance constraints apply only to active members. If a listed member is currently inactive, the constraint has no effect for that round.

---

## Complete Example

The following file demonstrates all four fields:

<!-- test: yaml fixture=full-example.yaml -->
```yaml
- name: Alice
  timezone: "UTC+0"

- name: Bob
  timezone: "UTC+0"
  avoid_buddies:
    - Charlie

- name: Charlie
  timezone: "UTC+0"

- name: Diana
  timezone: "America/New_York"

- name: Eve
  timezone: "America/New_York"

- name: Frank
  timezone: "America/New_York"
  active: false
```

In this roster:
- Frank is currently inactive and will not be paired.
- Bob will never be paired with Charlie.
- All other members can be paired with any other active member.

---

## Validation Errors

| Condition | Error type | Exit code |
|-----------|-----------|-----------|
| File not found or unreadable | File load error | 1 |
| Path is a directory | File load error | 1 |
| File is not valid UTF-8 | File load error | 1 |
| File is not valid YAML | File load error | 1 |
| File is empty | File load error | 1 |
| File is not a YAML list | File load error | 1 |
| A list entry is not a mapping | Validation error | 1 |
| `name` missing or empty | Validation error | 1 |
| `timezone` missing or empty | Validation error | 1 |
| Duplicate `name` | Validation error | 1 |
| `active` is not a boolean | Validation error | 1 |
| `avoid_buddies` is not a list | Validation error | 1 |
| `avoid_buddies` entry does not match any roster member name | Validation error | 1 |

---

## Related References

- **CLI options**: [cli.md](cli.md)
- **Output format**: [output-format.md](output-format.md)
