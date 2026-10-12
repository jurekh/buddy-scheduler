"""Unit tests for the YAML roster loader and validator."""

from __future__ import annotations

import textwrap
import unicodedata
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


class TestFileAccessErrors:
    """Tests for OSError handling in load_team_roster."""

    def test_team_path_is_directory(self, tmp_path: Path) -> None:
        """A directory path raises FileLoadError with a clear 'directory' message."""
        with pytest.raises(FileLoadError, match="directory"):
            load_team_roster(tmp_path)

    def test_permission_error_on_exists_raises_file_load_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PermissionError from path.exists() is wrapped in FileLoadError.

        Python 3.12+ propagates PermissionError from Path.exists() rather
        than silently returning False, so it must be caught explicitly.
        """
        import pathlib

        def raising_exists(self: pathlib.Path, **kwargs: object) -> bool:
            raise PermissionError(13, "Permission denied", str(self))

        monkeypatch.setattr(pathlib.Path, "exists", raising_exists)

        with pytest.raises(FileLoadError, match="Cannot access team roster file"):
            load_team_roster(tmp_path / "team.yaml")

    def test_permission_error_on_read_raises_file_load_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PermissionError from path.read_text() is wrapped in FileLoadError."""
        import pathlib

        p = tmp_path / "team.yaml"
        p.write_text("- name: Alice\n  timezone: UTC\n")

        original = pathlib.Path.read_text

        def raising_read_text(
            self: pathlib.Path, *args: object, **kwargs: object
        ) -> str:
            if self == p:
                raise PermissionError(13, "Permission denied", str(self))
            return original(self, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(pathlib.Path, "read_text", raising_read_text)

        with pytest.raises(FileLoadError, match="Cannot read team roster file"):
            load_team_roster(p)


class TestAvoidBuddiesCrossReference:
    """Tests for the second-pass avoid_buddies cross-reference validation."""

    def test_avoid_buddies_valid_reference(self, tmp_path: Path) -> None:
        """avoid_buddies entry that matches a roster member raises no error."""
        p = _write_yaml(
            tmp_path,
            """
            - name: Alice
              timezone: UTC
              avoid_buddies:
                - Bob
            - name: Bob
              timezone: UTC
            """,
        )
        members = load_team_roster(p)
        assert members[0].avoid_buddies == ["Bob"]

    def test_avoid_buddies_unknown_name(self, tmp_path: Path) -> None:
        """avoid_buddies entry matching no roster member raises DataValidationError."""
        p = _write_yaml(
            tmp_path,
            """
            - name: Alice
              timezone: UTC
              avoid_buddies:
                - Alic
            - name: Bob
              timezone: UTC
            """,
        )
        with pytest.raises(DataValidationError, match="Alice") as exc_info:
            load_team_roster(p)
        assert "Alic" in str(exc_info.value)

    def test_avoid_buddies_inactive_member_valid(self, tmp_path: Path) -> None:
        """avoid_buddies referencing inactive member is valid (still in roster)."""
        p = _write_yaml(
            tmp_path,
            """
            - name: Alice
              timezone: UTC
              avoid_buddies:
                - Charlie
            - name: Bob
              timezone: UTC
            - name: Charlie
              timezone: UTC
              active: false
            """,
        )
        members = load_team_roster(p)
        assert members[0].avoid_buddies == ["Charlie"]

    def test_avoid_buddies_self_reference_ignored(self, tmp_path: Path) -> None:
        """avoid_buddies self-reference is not a validation error."""
        p = _write_yaml(
            tmp_path,
            """
            - name: Alice
              timezone: UTC
              avoid_buddies:
                - Alice
            - name: Bob
              timezone: UTC
            """,
        )
        members = load_team_roster(p)
        assert members[0].avoid_buddies == ["Alice"]


class TestUnicodeNormalization:
    """NFC normalization behaviour for member names and avoid_buddies.

    Python string equality treats NFC and NFD forms as distinct, which would
    cause duplicate detection to miss visually identical names and break
    avoid_buddies cross-referencing.  The loader normalises all name strings
    to NFC so callers work with a single canonical form.
    """

    # "é" in NFD: base 'e' + combining acute (U+0301)
    _NFD = "e\u0301"
    # "é" in NFC: precomposed U+00E9
    _NFC = "\u00e9"

    def _yaml(self, name: str) -> str:
        return f"- name: {name}\n  timezone: UTC\n"

    def test_nfd_name_is_stored_as_nfc(self, tmp_path: Path) -> None:
        """A member name written in NFD form is normalised to NFC on load."""
        p = tmp_path / "team.yaml"
        p.write_text(self._yaml(self._NFD), encoding="utf-8")
        members = load_team_roster(p)
        assert members[0].name == self._NFC
        assert unicodedata.is_normalized("NFC", members[0].name)

    def test_nfc_name_is_preserved(self, tmp_path: Path) -> None:
        """A member name already in NFC form passes through unchanged."""
        p = tmp_path / "team.yaml"
        p.write_text(self._yaml(self._NFC), encoding="utf-8")
        members = load_team_roster(p)
        assert members[0].name == self._NFC

    def test_nfc_and_nfd_same_name_are_duplicates(self, tmp_path: Path) -> None:
        """NFC and NFD forms of the same name are treated as duplicate members."""
        p = tmp_path / "team.yaml"
        p.write_text(
            self._yaml(self._NFC) + self._yaml(self._NFD),
            encoding="utf-8",
        )
        with pytest.raises(DataValidationError, match="Duplicate"):
            load_team_roster(p)

    def test_nfd_avoid_buddy_resolves_nfc_name(self, tmp_path: Path) -> None:
        """An avoid_buddies entry in NFD form resolves against an NFC member name."""
        p = tmp_path / "team.yaml"
        p.write_text(
            textwrap.dedent(f"""\
            - name: {self._NFC}l\u00e9
              timezone: UTC
            - name: Bob
              timezone: UTC
              avoid_buddies:
                - {self._NFD}l\u00e9
            """),
            encoding="utf-8",
        )
        members = load_team_roster(p)
        assert members[1].avoid_buddies == ["\u00e9l\u00e9"]
