# Research: Snap Strict Confinement

**Branch**: `003-snap-strict` | **Date**: 2026-02-26

---

## Decision 1: override-build workaround

**Decision**: Remove the override-build block entirely for strict confinement.

**Rationale**: The workaround copies the host Python binary into the build
directory so that the Python plugin can construct a relative symlink rather
than an absolute build-host path. This is needed because, for classic
confinement, `get_system_interpreter()` in the snapcraft Python plugin returns
`None`, which causes the plugin to fall back to a `readlink`-based lookup of
whatever Python binary it finds — and if none is present in
`$CRAFT_PART_INSTALL/usr/bin/`, the resulting symlink points to an absolute
host path that does not exist at snap runtime.

For `confinement: strict` with `base: core24`, `get_system_interpreter()`
returns the hardcoded string `/usr/bin/python3.12`, and the plugin creates
`bin/python3 → /usr/bin/python3.12` as a stable relative target. The
`core24` base snap always has Python 3.12 at that path. The workaround is not
needed and should be removed.

Additionally, `post_prime()` in the plugin automatically patches `pyvenv.cfg`
so that `home =` points to `/snap/<name>/current` rather than a build-time
staging path. This eliminates another common source of runtime failures in
classic snaps that the workaround was partially compensating for.

**Alternatives considered**: Keeping the override-build — rejected because it
is specific to classic confinement and could interfere with the strict-mode
plugin's own symlink creation.

Sources: `python_common.py` in snapcraft 8.14.1;
https://documentation.ubuntu.com/snapcraft/stable/reference/plugins/python_plugin/

---

## Decision 2: PYTHONPATH and PATH environment variables

**Decision**: Remove both `PYTHONPATH` and `PATH` from the app's `environment:`
block. Use only `plugs:` in the app section.

**Rationale**: With strict confinement on `core24`, the Python plugin builds
a proper venv, patches `pyvenv.cfg` to use runtime paths, and rewrites the
entrypoint shebang to `#!/usr/bin/env python3`. The venv's path machinery
handles `sys.path` / `site-packages` at runtime without manual `PYTHONPATH`
overrides. Setting `PYTHONPATH` explicitly can override the venv's normal
resolution and cause packages from the wrong location to be loaded.

The manual `PYTHONPATH` and `PATH` settings in the current snapcraft.yaml were
workarounds for the broken `pyvenv.cfg` `home` value on classic snaps. With
strict confinement on core24, `pyvenv.cfg` is patched automatically and those
workarounds are not needed.

**Alternatives considered**: Keeping the environment variables — rejected
because they can mask venv configuration issues and are actively unnecessary.

---

## Decision 3: snap interface for home directory access

**Decision**: Add `plugs: [home]` to the app. No other interfaces are needed.

**Rationale**: The `home` interface grants read/write access to
`$HOME/[non-hidden files]` under AppArmor pattern `@{HOME}/[^s.]**`. This
covers `~/team.yaml`, `~/history.json`, and any file under a visible
subdirectory, which is the full set of paths that `--team` and `--history`
are expected to reference.

The `home` interface is auto-connected on `snap install` from the Snap Store.
On sideloaded installs (`snap install --dangerous`), it also auto-connects on
standard Ubuntu desktop and server systems (classic systems), because the
snapd `home` interface's built-in declaration includes:
`deny-auto-connection: on-classic: false` — meaning auto-connection is denied
only when `on-classic` is `false` (i.e. on Ubuntu Core IoT). On a standard
Ubuntu system, it auto-connects without a store assertion.

**Dotfile caveat**: `home` does not cover dotfiles (paths starting with `.`).
If a future feature stores config in `~/.config/buddy-scheduler/`, the
`personal-files` interface would be needed. This is out of scope for the
current feature.

**Alternatives considered**: `personal-files` — rejected as unnecessarily
restrictive and requiring explicit path declarations and store review.
`removable-media` — not needed; out of scope per spec assumptions.

Sources: https://snapcraft.io/docs/home-interface;
snapd `interfaces/builtin/home.go`

---

## Decision 4: build-packages

**Decision**: Remove `build-packages: [python3-dev]` from the part definition.

**Rationale**: The snapcraft Python plugin's `get_build_packages()` method
already returns `{"findutils", "python3-dev", "python3-venv"}` automatically.
Declaring it explicitly is redundant but harmless; removing it keeps the
manifest minimal and avoids confusion.

**Alternatives considered**: Keeping it — acceptable but creates false
impression that it would not be included otherwise.

---

## Decision 5: no new contracts or data-model changes

**Decision**: No contracts/ or data-model.md artifacts are needed for this
feature.

**Rationale**: This feature changes only the snap packaging manifest and one
documentation page. The CLI interface, input/output schema, and data model are
entirely unchanged. The existing CLI contracts from `001-buddy-scheduler`
remain valid.

---

## Summary of snapcraft.yaml changes

```yaml
# Before (classic)
confinement: classic

parts:
  buddy-scheduler:
    plugin: python
    source: .
    build-packages:
      - python3-dev
    override-build: |
      python_bin="$(readlink -f /usr/bin/python3)"
      python_name="$(basename "$python_bin")"
      mkdir -p "$CRAFT_PART_INSTALL/usr/bin"
      cp "$python_bin" "$CRAFT_PART_INSTALL/usr/bin/$python_name"
      craftctl default

apps:
  buddy-scheduler:
    command: bin/buddy-scheduler
    environment:
      PATH: $SNAP/usr/bin:$SNAP/bin:$PATH
      PYTHONPATH: $SNAP/lib/python3.12/site-packages:...

# After (strict)
confinement: strict

parts:
  buddy-scheduler:
    plugin: python
    source: .

apps:
  buddy-scheduler:
    command: bin/buddy-scheduler
    plugs:
      - home
```
