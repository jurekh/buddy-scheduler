# How to Configure Avoidance Constraints

This guide explains how to prevent specific pairs from ever forming — for example, a manager and their direct report who already meet regularly.

**Prerequisite**: You have completed the [Getting Started tutorial](../tutorial/getting-started.md) and have a working `team.yaml` file.

---

## Step 1: Add an avoidance constraint

Open your `team.yaml` file and add an `avoid_buddies` list to the member who should never be paired with specific others.

In this example, Bob is the manager and Alice is their direct report. Add `avoid_buddies` to Bob's entry:

<!-- test: yaml fixture=with-avoidance.yaml -->
```yaml
- name: Alice
  timezone: "UTC+0"

- name: Bob
  timezone: "UTC+0"
  avoid_buddies:
    - Alice

- name: Charlie
  timezone: "America/New_York"

- name: Diana
  timezone: "America/New_York"
```

The `avoid_buddies` list contains names of members that this person should never be paired with. The constraint is symmetric — if Bob avoids Alice, Alice will also never be paired with Bob, regardless of whether Alice's entry also lists Bob.

---

## Step 2: Run the tool and verify the constraint

<!-- test: cli fixture=with-avoidance.yaml exit=0 -->
```bash
buddy-scheduler --team team.yaml
```

The output will not contain the pair `["Alice", "Bob"]` in `pairs`:

```json
{
  "success": true,
  "pairs": [
    ["Alice", "Charlie"],
    ["Bob", "Diana"]
  ],
  "sitting_out": null,
  "optimization_score": 1.0,
  "solve_time": 0.038,
  "solver_profile": "optimal",
  "history_updated": false
}
```

Alice and Bob are in different pairs. Avoidance constraints are never relaxed — the pair will never appear regardless of history or timezone settings.

---

## Step 3: Handle impossible constraints

If avoidance constraints are so restrictive that no valid pairing exists (for example, a team member avoids every other active member), the tool exits with code 1 and explains the conflict:

```json
{
  "success": false,
  "pairs": [],
  "sitting_out": null,
  "optimization_score": 0.0,
  "solve_time": 0.012,
  "solver_profile": "optimal",
  "history_updated": false,
  "avoidance_conflicts": [
    "Alice has no eligible pairing partners"
  ],
  "error": "Infeasible: avoidance constraints prevent a valid pairing."
}
```

To resolve this, reduce the number of avoidance entries for the affected member, or deactivate some constraints by removing entries from `avoid_buddies`.

---

## Step 4: Fix an unrecognised name error

If a name in `avoid_buddies` does not exactly match any member's `name` field, the tool exits with a validation error before attempting to solve:

**Roster file with a typo:**

<!-- test: yaml fixture=unknown-avoid-buddy.yaml -->
```yaml
- name: Alice
  timezone: "UTC+0"
  avoid_buddies:
    - Alic

- name: Bob
  timezone: "UTC+0"

- name: Charlie
  timezone: "America/New_York"

- name: Diana
  timezone: "America/New_York"
```

Running the tool against this file produces an error (exit code 1):

<!-- test: cli fixture=unknown-avoid-buddy.yaml exit=1 -->
```bash
buddy-scheduler --team team.yaml
```

**Error output (exit code 1):**

```json
{
  "success": false,
  "error": "Member 'Alice' has unrecognised avoid_buddies entry 'Alic' — no member named 'Alic' exists in the roster"
}
```

The error message identifies the member whose entry contains the problem and the unrecognised name. Correct the typo in `team.yaml` to fix it. Names are case-sensitive.

---

## Notes

- `avoid_buddies` is optional; omit it entirely if no avoidance is needed for a member.
- The constraint is symmetric: you only need to list the avoidance on one side.
- Avoidance constraints apply only to active members. If a member in `avoid_buddies` is currently inactive, the constraint has no effect for that round.
- Names in `avoid_buddies` must exactly match the `name` field of another roster member (including capitalisation). An unrecognised name is always a validation error.
