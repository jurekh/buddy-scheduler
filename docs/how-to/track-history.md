# How to Track Pairing History Across Rounds

This guide explains how to carry pairing history between rounds so that the tool avoids repeating the same pairs.

**Prerequisite**: You have completed the [Getting Started tutorial](../tutorial/getting-started.md) and have a working `team.yaml` file.

---

## Step 1: Run with history enabled

Add `--update-history` to your command. This tells the tool to record the pairings from this run:

<!-- test: cli fixture=minimal.yaml exit=0 -->
```bash
buddy-scheduler --team team.yaml --update-history
```

The tool creates a history file automatically the first time. The file is named after your team file: if your team file is `team.yaml`, the history file will be `team.history.json` in the same directory.

You can also specify an explicit history file path with `--history`:

```bash
buddy-scheduler --team team.yaml --history my-history.json --update-history
```

After a successful run, the output will show `"history_updated": true`.

---

## Step 2: Run the next round

Run the same command again for the next pairing round:

```bash
buddy-scheduler --team team.yaml --update-history
```

The tool reads the history file and assigns higher penalties to pairs that have been together recently. Members who have not been paired recently are preferred. The second round should produce different pairings from the first.

---

## Step 3: Verify the history is being used

Check `optimization_score` in the output. When history is loaded, previously paired members receive a penalty, so the score will be greater than `0.0` if the solver had to work around any repeated pairs.

---

## Step 4: Remove a departed team member from history

When a team member leaves, their history entries can accumulate and affect future pairing scores. Use `--prune-history` to remove entries for members no longer in your roster:

```bash
buddy-scheduler --team team.yaml --update-history --prune-history
```

`--prune-history` removes history entries for any member who is not currently in `team.yaml`. It has no effect without `--update-history` — if you pass `--prune-history` alone, the tool emits a warning and continues normally:

<!-- test: cli fixture=minimal.yaml exit=0 -->
```bash
buddy-scheduler --team team.yaml --prune-history
```

---

## What the history file contains

The history file is a JSON file managed by the tool. You do not need to edit it directly. The tool records how many times each pair has been together and how many times each member has sat out. This information is used to weight the pairing objective in the next round.

If the history file does not exist when you run with `--update-history`, the tool creates it automatically with an empty record — no manual setup is needed.
