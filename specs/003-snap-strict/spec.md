# Feature Specification: Snap Strict Confinement

**Feature Branch**: `003-snap-strict`
**Created**: 2026-02-26
**Status**: Draft
**Input**: User description: "Switch snap to strict confinement"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Install without --classic (Priority: P1)

A Linux user installs buddy-scheduler from the Snap Store using the standard
`sudo snap install buddy-scheduler` command, with no flags. The installation
succeeds and the tool works correctly with files stored in their home directory.

**Why this priority**: Removing the `--classic` requirement is the core
objective. Everything else is a consequence of achieving it.

**Independent Test**: Build the snap locally, sideload it with
`--dangerous` (no `--classic`), run `buddy-scheduler --team ~/team.yaml`,
and confirm it produces valid JSON output.

**Acceptance Scenarios**:

1. **Given** a built snap package, **When** a user installs it without
   `--classic`, **Then** the installation completes without a
   "classic confinement" warning and the command is available.
2. **Given** the snap is installed, **When** the user runs
   `buddy-scheduler --team ~/team.yaml`, **Then** the tool reads the file and
   produces valid JSON output.
3. **Given** the snap is installed, **When** the user runs
   `buddy-scheduler --team ~/team.yaml --update-history`, **Then** the tool
   writes the history file to the same directory without a permission error.

---

### User Story 2 — Snap Store eligibility (Priority: P2)

Because the snap uses strict confinement, it is eligible for automated Snap
Store review rather than the manual review process required for classic snaps,
removing a publication bottleneck.

**Why this priority**: Matters for distribution, but the snap can still be
sideloaded without it.

**Independent Test**: Verify the built snap passes local Snap Store review
tooling without classic-confinement warnings.

**Acceptance Scenarios**:

1. **Given** the snap package, **When** reviewed with Snap Store review tools,
   **Then** no classic-confinement violation or warning is reported.
2. **Given** the snap is published to the Snap Store, **When** a user views its
   listing, **Then** no "classic confinement" label is shown.

---

### Edge Cases

- What happens when `--team` or `--history` points to a path blocked by
  confinement (e.g., `/root/team.yaml`, `/etc/teams/roster.yaml`)? The OS
  returns a permission error; the tool must surface a clear, readable
  file-load error — not a silent failure or an unhandled exception. Note:
  `/tmp/` is accessible to all strictly confined snaps (permitted by snapd's
  base AppArmor policy) and is not a confinement boundary.
- What happens if a user was previously relying on classic access to system
  paths? They must move their files into `$HOME`. The documentation must
  reflect the new access boundary.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The snap package MUST install on Linux without requiring the
  `--classic` flag.
- **FR-002**: The installed snap MUST be able to read team roster files from
  any path within the user's home directory.
- **FR-003**: The installed snap MUST be able to read and write history files
  to any path within the user's home directory.
- **FR-004**: The snap MUST NOT require filesystem access outside of the user's
  home directory for its primary use cases.
- **FR-005**: When the snap is denied access to a file due to confinement, the
  tool MUST surface a clear file-not-accessible error message rather than
  crashing or failing silently.
- **FR-006**: The snap package description MUST accurately describe the tool
  with no references to removed features.
- **FR-007**: The getting-started tutorial MUST be updated to remove the
  `--classic` flag from the snap installation command.

### Key Entities

- **Snap confinement policy**: The access control model declared in the snap
  manifest. Determines which filesystem paths the snap may access at runtime.
- **`home` interface**: The snap interface that grants read/write access to the
  user's home directory under strict confinement. Must be declared as a plug
  in the manifest and auto-connects on Snap Store installation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The snap installs with `sudo snap install buddy-scheduler` and no
  additional flags.
- **SC-002**: The tool successfully reads and writes files anywhere within
  `$HOME` when running as a strictly confined snap.
- **SC-003**: The snap passes local Snap Store review tooling without any
  classic-confinement warning.
- **SC-004**: The getting-started tutorial no longer includes `--classic` in
  the snap installation command.
- **SC-005**: Attempting to read a file outside `$HOME` via the snap produces a
  clear error message identifying the file as inaccessible, not an unhandled
  exception.

## Assumptions

- The primary use case is team roster and history files stored in the user's
  home directory. Access to paths under `/etc/`, `/mnt/`, or network mounts is
  out of scope; users with those requirements should use the Python package
  install path instead.
- The `home` interface is sufficient; `removable-media` (for `/media`, `/mnt`)
  is not added unless a follow-up feature requests it.
- The snap targets the Snap Store distribution path. Sideloading with
  `--dangerous` (and no `--classic`) is used for local testing only.

## Dependencies

- `snap/snapcraft.yaml` — confinement declaration and app plugs
- `docs/tutorial/getting-started.md` — snap installation instructions
