# Quickstart: buddy-scheduler

## Install

```bash
# From source (development)
git clone <repo>
cd buddy-scheduler
make setup          # installs uv + creates venv + installs package in editable mode

# From PyPI (once published)
pip install buddy-scheduler

# As a snap
sudo snap install buddy-scheduler
```

## Prepare a team file

Create `team.yaml`:

```yaml
- name: Alice
  timezone: "UTC+0"

- name: Bob
  timezone: "UTC+0"

- name: Charlie
  timezone: "America/New_York"

- name: Diana
  timezone: "America/New_York"

- name: Eve
  timezone: "Asia/Tokyo"
  avoid_buddies:
    - Frank

- name: Frank
  timezone: "Asia/Tokyo"
```

## Generate pairings (no history)

```bash
buddy-scheduler --team team.yaml
```

Output (stdout):
```json
{
  "success": true,
  "pairs": [["Alice", "Bob"], ["Charlie", "Diana"], ["Eve", "Frank"]],
  "sitting_out": null,
  "solver_profile": "balanced",
  ...
}
```

## Generate pairings with history tracking

```bash
# First run — creates history.json automatically
buddy-scheduler --team team.yaml --history history.json --update-history

# Subsequent runs — avoids repeating pairs from history
buddy-scheduler --team team.yaml --history history.json --update-history
```

## Prune departed members from history

```bash
buddy-scheduler --team team.yaml --history history.json \
  --update-history --prune-history
```

## Tune optimisation weights

```bash
# Prioritise timezone compatibility over history avoidance
buddy-scheduler --team team.yaml --history history.json \
  --tz-weight 2.0 --history-weight 0.5
```

## Use a specific solver profile

```bash
# Fast (wide gap tolerance — for large teams or quick previews)
buddy-scheduler --team team.yaml --solver-profile fast

# Optimal (tight gap tolerance — for small teams where quality matters most)
buddy-scheduler --team team.yaml --solver-profile optimal
```

## Adjust logging

```bash
# Verbose (debug all operations)
buddy-scheduler --team team.yaml --log-level DEBUG

# Quiet (errors only)
buddy-scheduler --team team.yaml --log-level ERROR
```

## Consume output programmatically

```bash
# Pipe JSON output to jq
buddy-scheduler --team team.yaml | jq '.pairs'

# Check success in a shell script
if buddy-scheduler --team team.yaml --history history.json --update-history; then
  echo "Pairings generated"
else
  echo "Failed — check stderr for details"
fi
```

## Development commands

```bash
make install        # Install project + dev deps via uv
make test           # Run tests (excludes slow tests), print coverage
make lint           # Run ruff check
make format         # Auto-format with ruff
make typecheck      # Run mypy in strict mode
make all            # install → test → lint → typecheck
make build          # Build distributable wheel
make clean          # Remove build artefacts
```
