# Quickstart: Building and Testing the Strict-Confinement Snap

**Branch**: `003-snap-strict`

This guide covers how to build the snap locally and verify that strict
confinement works correctly with the `home` interface.

---

## Prerequisites

- snapcraft installed: `sudo snap install snapcraft --classic`
- snapd running: `sudo systemctl status snapd`
- LXD available (recommended for clean builds):
  `sudo snap install lxd && sudo lxd init --minimal`

---

## Build the snap

```bash
snapcraft --use-lxd
```

This produces `buddy-scheduler_0.1.0_amd64.snap` (or `arm64` on ARM).

---

## Sideload and verify

Install without `--classic`:

```bash
sudo snap install --dangerous buddy-scheduler_0.1.0_amd64.snap
```

Check that the `home` interface auto-connected:

```bash
snap connections buddy-scheduler
```

Expected output includes:
```
Interface  Plug                        Slot   Notes
home       buddy-scheduler:home        :home  -
```

If `home` shows as `-` (not connected), connect it manually:

```bash
sudo snap connect buddy-scheduler:home :home
```

---

## Smoke tests

**Basic run with a file in $HOME**:

```bash
cp tests/fixtures/minimal.yaml ~/team.yaml
buddy-scheduler --team ~/team.yaml
```

Expected: valid JSON output with `"success": true`.

**History write in $HOME**:

```bash
buddy-scheduler --team ~/team.yaml --update-history
ls ~/team.history.json
```

Expected: history file created.

**File blocked by confinement (should fail cleanly)**:

```bash
sudo cp tests/fixtures/minimal.yaml /root/team.yaml
buddy-scheduler --team /root/team.yaml
```

Expected: exit code 1 with a JSON error document containing a readable
file-load error message, not a Python traceback.

Note: `/tmp/` is accessible to all strictly confined snaps — it is
explicitly permitted in snapd's base AppArmor policy and is not a useful
test of confinement boundaries. Use `/root/` or another system path to
verify that confinement is actually enforced.

---

## Verify no --classic required

Confirm the snap info does not show classic confinement:

```bash
snap info buddy-scheduler | grep confinement
```

Expected: `confinement: strict`

---

## Clean up

```bash
sudo snap remove buddy-scheduler
rm ~/team.yaml ~/team.history.json
```
