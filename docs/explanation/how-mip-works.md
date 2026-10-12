# How the Pairing Algorithm Works

This document explains the reasoning behind how buddy-scheduler produces pairings. Reading it is not required to use the tool, but it helps if you want to understand why a particular pairing was chosen, or how to tune the weights for your team.

---

## What problem the tool solves

Given a team roster, the tool assigns every active member to exactly one pair for the current round. When the active team has an odd number of members, one person sits out. The tool tries to choose pairs that respect avoidance constraints, avoid repeating recent pairs, and keep members in similar timezones together.

These objectives conflict: a pair that is historically fresh might span very different timezones. The tool uses a mathematical optimisation formulation to find the best tradeoff.

---

## The objective function

The tool minimises a weighted penalty sum over all candidate pairs:

> **Minimise** sum ( `history_weight` * `pair_count(a, b)` + `tz_weight` * `tz_penalty(a, b)` ) * `x(a, b)`

where:

- `x(a, b)` is a binary decision variable that equals 1 if members *a* and *b* are paired in this round
- `pair_count(a, b)` is the number of times *a* and *b* have been paired in the recorded history
- `tz_penalty(a, b)` is a value in [0, 1] reflecting how different the timezone labels of *a* and *b* are (0 = identical labels, 1 = no characters in common)
- `history_weight` and `tz_weight` are the `--history-weight` and `--tz-weight` parameters you supply

Raising `--history-weight` causes the solver to try harder to avoid repeating pairs that have appeared frequently in history. Setting `--history-weight 0.0` disables the history penalty on pairs - pairings are then chosen based solely on timezone compatibility. The sit-out cost (see below) is not scaled by this weight, so sit-out fairness still applies.

Raising `--tz-weight` causes the solver to try harder to pair members whose timezone labels are similar. Setting `--tz-weight 0.0` disables timezone scoring - pairings are then based solely on history.

The `optimization_score` field in the output is the value of this sum for the solution that was found. A score of `0.0` means no history penalty and no timezone penalty accumulated.

---

## Hard constraints

Two constraints are never relaxed, regardless of the penalty weights:

**Coverage constraint**: Every active member must appear in exactly one pair (or sit out, for odd teams). No member can be in two pairs, and no member can be left without a pair.

**Avoidance constraint**: Pairs listed in `avoid_buddies` are excluded from consideration entirely. The binary variable `x(a, b)` is simply not created for a forbidden pair, so the solver cannot select it.

Because avoidance constraints are hard, an over-constrained team (for example, a member who avoids every other active member) produces an infeasible problem. The tool reports this immediately with an exit code of 1 and lists the affected members in the `avoidance_conflicts` field.

---

## Sit-out fairness

When the active team has an odd number of members, exactly one person sits out. The tool adds their sit-out cost to the objective alongside pair costs:

> **Sit-out cost for member a** = (number of times *a* has sat out in recorded history) * `sit_out_variable(a)`

This means the solver prefers to assign the sit-out to whoever has sat out least often in the history. Members who have never sat out are preferred over those who have sat out many times.

When no history is loaded, all sit-out costs are zero and the solver chooses the sit-out member based on how it affects the pairing of the remaining members.

---

## Timezone scoring

The tool does not parse timezone strings against any standard timezone database. Instead, it measures string similarity between the timezone labels as written in the roster file.

The `tz_penalty` between two labels is computed as:

> `tz_penalty(a, b)` = 1 - `SequenceMatcher.ratio(label_a, label_b)`

A ratio of 1.0 means the strings are identical -> penalty 0.0. A ratio of 0.0 means the strings share no characters -> penalty 1.0.

**Practical implication**: The scoring only works as intended if your team uses consistent label formats. Members with labels `"UTC+0"` and `"UTC+0"` score zero penalty - the solver recognises them as timezone-compatible. Members with labels `"UTC+1"` and `"Europe/Paris"` score a moderate penalty even if they work in the same timezone, because the strings are textually different. Using consistent labels across your entire roster (for example, always using `"America/New_York"` rather than mixing `"EST"`, `"UTC-5"`, and `"New York"`) improves the quality of timezone-based grouping.

---

## Solver profiles

The MIP solver (CBC, via PuLP) searches for an optimal assignment, but for large teams the search space grows quickly. Solver profiles control how much time and how much optimality the solver trades:

**Gap tolerance**: The solver can stop early when the best solution it has found is within a certain percentage of the theoretical optimum. A tolerance of 1% means the solver may return a solution that is at most 1% worse than the globally optimal solution. A tolerance of 0.1% means it will search longer to get closer to the optimum.

**Time limit**: The solver stops after this many seconds regardless of gap, returning the best solution found so far.

The four profiles are:

| Profile | Gap tolerance | Time limit | Adaptive selection threshold |
|---------|--------------|------------|------------------------------|
| `optimal` | 0.1% | 300 s | Active team <= 15 members |
| `balanced` | 1% | 60 s | Active team 16-60 members |
| `fast` | 20% | 10 s | Active team > 60 members |
| `adaptive` | (automatic) | (automatic) | Selects based on team size |

The default profile is `adaptive`. For teams of 60 or fewer active members, `adaptive` selects `optimal` (up to 15) or `balanced` (16 to 60). For larger teams it selects `fast`, which shortens runtime at the cost of a larger allowed gap from the optimum.

You can override the selection with `--solver-profile` if the default is not appropriate for your situation. See the [CLI reference](../reference/cli.md) for details.

The `solver_profile` field in the output always shows the resolved profile name - `"optimal"`, `"balanced"`, or `"fast"` - never `"adaptive"`.
