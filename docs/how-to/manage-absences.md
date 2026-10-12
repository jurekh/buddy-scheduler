# How to Manage Absent Team Members

This guide explains how to temporarily exclude a team member from pairing without removing them from the roster, and how to reactivate them when they return.

**Prerequisite**: You have completed the [Getting Started tutorial](../tutorial/getting-started.md) and have a working `team.yaml` file.

---

## Step 1: Mark a member as inactive

Open your `team.yaml` file and add `active: false` to the entry for the absent member:

<!-- test: yaml fixture=with-absence.yaml -->
```yaml
- name: Alice
  timezone: "UTC+0"

- name: Bob
  timezone: "UTC+0"

- name: Charlie
  timezone: "UTC+0"
  active: false

- name: Diana
  timezone: "America/New_York"
```

In this example, Charlie is on leave and will be excluded from the next pairing round.

---

## Step 2: Run the tool

<!-- test: cli fixture=with-absence.yaml exit=0 -->
```bash
buddy-scheduler --team team.yaml
```

The output will confirm Charlie is excluded. The `inactive_members` field in the output lists all members who were skipped because `active` is `false`:

```json
{
  "success": true,
  "pairs": [
    ["Alice", "Bob"]
  ],
  "sitting_out": "Diana",
  "optimization_score": 0.0,
  "solve_time": 0.031,
  "solver_profile": "optimal",
  "history_updated": false,
  "peak_memory_mb": 36.1,
  "memory_delta_mb": 0.02,
  "inactive_members": ["Charlie"]
}
```

Charlie does not appear in `pairs` or `sitting_out`. Their history is preserved - when they return, prior pairing data is still used to inform future pairings.

---

## Step 3: Reactivate the member

When the member returns, remove `active: false` from their entry (or set it back to `active: true`):

```yaml
- name: Alice
  timezone: "UTC+0"

- name: Bob
  timezone: "UTC+0"

- name: Charlie
  timezone: "UTC+0"

- name: Diana
  timezone: "America/New_York"
```

Run the tool again. Charlie is now included in the pairing:

<!-- test: cli fixture=minimal.yaml exit=0 -->
```bash
buddy-scheduler --team team.yaml
```

---

## Notes

- `active` defaults to `true` - you only need to specify it when setting it to `false`.
- Inactive members are not counted when determining whether the team has an odd or even number of members. If removing inactive members results in an odd active count, one active member will sit out.
- The history file is not affected by marking a member as inactive. Their historical pair counts and sit-out counts are retained and will be used when they rejoin.
- To permanently remove a member from history after they leave the team, see [How to track pairing history](track-history.md) for the `--prune-history` option.
