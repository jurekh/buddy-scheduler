"""Unit tests for the YAML roster loader and validator."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from buddy_scheduler.models import DataValidationError, FileLoadError
from buddy_scheduler.validator import load_team_roster


def _write_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "team.yaml"
    p.write_text(textwrap.dedent(content))
    return p


class TestLoadTeamRoster:
    """Integration-level tests for the YAML loader."""

    def test_valid_roster_loads_correctly(self, tmp_path: Path) -> None:
        p = _write_yaml(
            tmp_path,
            """
            - name: Alice
              timezone: "UTC+0"
            - name: Bob
              timezone: "America/New_York"
              active: false
              avoid_buddies:
                - Alice
            """,
        )
        members = load_team_roster(p)
        assert len(members) == 2
        assert members[0].name == "Alice"
        assert members[0].timezone == "UTC+0"
        assert members[0].active is True
        assert members[1].active is False
        assert members[1].avoid_buddies == ["Alice"]

    def test_missing_file_raises_file_load_error(self, tmp_path: Path) -> None:
        with pytest.raises(FileLoadError, match="not found"):
            load_team_roster(tmp_path / "nonexistent.yaml")

    def test_empty_file_raises_file_load_error(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.yaml"
        p.write_text("")
        with pytest.raises(FileLoadError, match="empty"):
            load_team_roster(p)

    def test_non_list_yaml_raises_file_load_error(self, tmp_path: Path) -> None:
        p = _write_yaml(tmp_path, "name: Alice\ntimezone: UTC\n")
        with pytest.raises(FileLoadError, match="list"):
            load_team_roster(p)

    def test_invalid_yaml_raises_file_load_error(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.yaml"
        p.write_text("{ bad: yaml: ][")
        with pytest.raises(FileLoadError, match="YAML"):
            load_team_roster(p)

    def test_duplicate_names_raises_data_validation_error(
        self, tmp_path: Path
    ) -> None:
        p = _write_yaml(
            tmp_path,
            """
            - name: Alice
              timezone: UTC
            - name: Alice
              timezone: Europe/London
            """,
        )
        with pytest.raises(DataValidationError, match="Duplicate"):
            load_team_roster(p)

    def test_missing_timezone_raises_data_validation_error(
        self, tmp_path: Path
    ) -> None:
        p = _write_yaml(tmp_path, "- name: Alice\n")
        with pytest.raises(DataValidationError, match="timezone"):
            load_team_roster(p)

    def test_missing_name_raises_data_validation_error(
        self, tmp_path: Path
    ) -> None:
        p = _write_yaml(tmp_path, "- timezone: UTC\n")
        with pytest.raises(DataValidationError, match="name"):
            load_team_roster(p)

    def test_non_bool_active_raises_data_validation_error(
        self, tmp_path: Path
    ) -> None:
        p = _write_yaml(
            tmp_path, "- name: Alice\n  timezone: UTC\n  active: yes_string\n"
        )
        with pytest.raises(DataValidationError, match="active"):
            load_team_roster(p)

    def test_zero_active_members_is_valid(self, tmp_path: Path) -> None:
        """Validation passes even with zero active members (solver handles this)."""
        p = _write_yaml(
            tmp_path,
            """
            - name: Alice
              timezone: UTC
              active: false
            """,
        )
        members = load_team_roster(p)
        assert len(members) == 1
        assert members[0].active is False

    def test_avoid_buddies_as_list_is_valid(self, tmp_path: Path) -> None:
        p = _write_yaml(
            tmp_path,
            """
            - name: Alice
              timezone: UTC
              avoid_buddies:
                - Bob
                - Charlie
            - name: Bob
              timezone: UTC
            - name: Charlie
              timezone: UTC
            """,
        )
        members = load_team_roster(p)
        assert members[0].avoid_buddies == ["Bob", "Charlie"]

    def test_non_list_avoid_buddies_raises_data_validation_error(
        self, tmp_path: Path
    ) -> None:
        p = _write_yaml(
            tmp_path,
            "- name: Alice\n  timezone: UTC\n  avoid_buddies: Bob\n",
        )
        with pytest.raises(DataValidationError, match="avoid_buddies"):
            load_team_roster(p)
