# Getting Started with buddy-scheduler

This tutorial walks you through installing buddy-scheduler, creating your first team roster file, and generating your first buddy pairing. No prior knowledge of the tool is required.

By the end you will have a working installation and will have generated and read your first pairing output.

---

## Prerequisites

- A terminal (Linux or macOS; Windows users should use WSL)
- Python 3.11 or later (for the Python package installation path)

---

## Step 1: Install buddy-scheduler

Choose the option that matches your situation.

### Option A: Run from a cloned repository (no install required)

If you have cloned the repository, [uv](https://docs.astral.sh/uv/) can run
the tool directly from the project source without a separate install step:

```bash
uv run buddy-scheduler --help
```

All subsequent `buddy-scheduler` commands in this tutorial can be prefixed with
`uv run` when using this option.

### Option B: Install from a local source checkout

To install the tool into your uv tool environment from a local checkout:

```bash
uv tool install .
```

Verify the installation:

```bash
buddy-scheduler --help
```

### Option C: Install from PyPI

Install the published package using [uv](https://docs.astral.sh/uv/):

```bash
uv tool install buddy-scheduler
```

Verify the installation:

```bash
buddy-scheduler --help
```

### Option D: Snap package (Linux only)

```bash
sudo snap install buddy-scheduler
```

Verify the installation:

```bash
buddy-scheduler --help
```

---

## Step 2: Create a team roster file

buddy-scheduler reads your team from a YAML file. Create a file called `team.yaml` with the following content:

```yaml
- name: Alice
  timezone: "UTC+0"

- name: Bob
  timezone: "UTC+0"

- name: Charlie
  timezone: "America/New_York"

- name: Diana
  timezone: "America/New_York"
```

Each entry represents one team member. The only required fields are `name` (a unique string) and `timezone` (a free-form string describing where the person works). The file accepts any team size.

---

## Step 3: Generate your first pairing

Run the tool with your team file. No history is loaded and no history is saved — this is a dry run:

<!-- test: cli fixture=minimal.yaml exit=0 -->
```bash
buddy-scheduler --team team.yaml
```

You will see JSON output printed to your terminal, similar to:

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
  "history_updated": false
}
```

---

## Step 4: Read the output

Every field in the output is described below.

| Field | What it means |
|-------|---------------|
| `success` | `true` if a valid pairing was found; `false` if the tool could not produce one (see `error`) |
| `pairs` | List of pairs produced for this round. Each pair is a two-element list of member names, sorted alphabetically within the pair. |
| `sitting_out` | The name of the member who sits out this round (only when the active team has an odd number of members); `null` otherwise |
| `optimization_score` | The total penalty score the solver minimised. Lower is better. `0.0` means no history penalty and no timezone mismatch penalty. |
| `solve_time` | Time in seconds taken by the MIP solver |
| `solver_profile` | The solver profile that was used (`fast`, `balanced`, `optimal`). When you pass `--solver-profile adaptive` (the default), this shows the profile that was selected for your team size. |
| `history_updated` | `true` if the history file was updated during this run; `false` if this was a dry run |

In the example above, Alice and Bob are paired together (both `UTC+0`), and Charlie and Diana are paired together (both `America/New_York`). The tool preferred to pair members who share the same timezone.

---

## What's next

- To carry pairing history across rounds so the same pairs are not repeated, see [How to track pairing history](../how-to/track-history.md).
- To mark a team member as temporarily inactive (for example, when they are on leave), see [How to manage absent team members](../how-to/manage-absences.md).
- To prevent specific pairs from ever forming (for example, a manager and their direct report), see [How to configure avoidance constraints](../how-to/avoid-pairings.md).
- For a complete reference of all CLI options, see [CLI reference](../reference/cli.md).
