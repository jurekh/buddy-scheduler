"""YAML team roster loader and validator."""

from __future__ import annotations

import logging
import unicodedata
from pathlib import Path
from typing import Any

import yaml

from buddy_scheduler.models import DataValidationError, FileLoadError, TeamMember

logger = logging.getLogger(__name__)


def load_team_roster(path: Path) -> list[TeamMember]:
    """Load and validate a team roster from a YAML file.

    Args:
        path: Path to the YAML roster file.

    Returns:
        List of :class:`TeamMember` objects parsed from the file.

    Raises:
        FileLoadError: If the file is missing, unreadable, empty, or not a
            valid YAML list.
        DataValidationError: If any member entry is structurally or
            semantically invalid.
    """
    try:
        exists = path.exists()
    except OSError as exc:
        raise FileLoadError(f"Cannot access team roster file {path}: {exc}") from exc

    if not exists:
        raise FileLoadError(f"Team roster file not found: {path}")

    if path.is_dir():
        raise FileLoadError(f"Team roster path is a directory, not a file: {path}")

    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise FileLoadError(f"Team roster file contains invalid UTF-8: {path}") from exc
    except OSError as exc:
        raise FileLoadError(f"Cannot read team roster file {path}: {exc}") from exc

    try:
        data: Any = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise FileLoadError(f"Team roster file is not valid YAML: {exc}") from exc

    if not data:
        raise FileLoadError(f"Team roster file is empty: {path}")

    if not isinstance(data, list):
        raise FileLoadError(
            f"Team roster file must contain a YAML list of members, "
            f"got {type(data).__name__}: {path}"
        )

    members: list[TeamMember] = []
    seen_names: set[str] = set()

    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise DataValidationError(
                f"Member entry {i} must be a mapping, got {type(entry).__name__}"
            )

        name = entry.get("name")
        if not name or not isinstance(name, str):
            raise DataValidationError(
                f"Member entry {i}: 'name' is required and must be a non-empty string"
            )
        name = unicodedata.normalize("NFC", name)

        timezone = entry.get("timezone")
        if not timezone or not isinstance(timezone, str):
            raise DataValidationError(
                f"Member '{name}': 'timezone' is required and must be a "
                f"non-empty string"
            )

        if name in seen_names:
            raise DataValidationError(f"Duplicate member name: '{name}'")
        seen_names.add(name)

        active = entry.get("active", True)
        if not isinstance(active, bool):
            raise DataValidationError(
                f"Member '{name}': 'active' must be a boolean, "
                f"got {type(active).__name__}"
            )

        avoid_buddies = entry.get("avoid_buddies", [])
        if not isinstance(avoid_buddies, list):
            raise DataValidationError(
                f"Member '{name}': 'avoid_buddies' must be a list, "
                f"got {type(avoid_buddies).__name__}"
            )

        members.append(
            TeamMember(
                name=name,
                timezone=timezone,
                active=active,
                avoid_buddies=[
                    unicodedata.normalize("NFC", str(x)) for x in avoid_buddies
                ],
            )
        )

    # Second pass: cross-reference avoid_buddies entries against all known names
    all_names = {m.name for m in members}
    for member in members:
        for buddy in member.avoid_buddies:
            if buddy not in all_names:
                raise DataValidationError(
                    f"Member '{member.name}' has unrecognised avoid_buddies entry "
                    f"'{buddy}' — no member named '{buddy}' exists in the roster"
                )

    logger.info("Loaded %d members from %s", len(members), path)
    return members
