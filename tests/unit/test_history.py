"""Unit tests for the history store loader and writer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from buddy_scheduler.history import empty_history, load_history, save_history
from buddy_scheduler.models import DataValidationError, FileLoadError, PairingHistory


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


class TestLoadHistory:
    def test_valid_history_loads_correctly(self, tmp_path: Path) -> None:
        p = tmp_path / "history.json"
        _write_json(
            p,
            {
                "pair_counts": {
                    "Alice": {"Bob": 2},
                    "Bob": {"Alice": 2},
                },
                "sit_out_counts": {"Charlie": 1},
            },
        )
        h = load_history(p)
        assert h.get_pair_count("Alice", "Bob") == 2
        assert h.get_pair_count("Bob", "Alice") == 2
        assert h.sit_out_counts["Charlie"] == 1

    def test_missing_file_raises_file_load_error(self, tmp_path: Path) -> None:
        with pytest.raises(FileLoadError, match="not found"):
            load_history(tmp_path / "no-such-file.json")

    def test_directory_path_raises_file_load_error(self, tmp_path: Path) -> None:
        """A directory path raises FileLoadError with a clear 'directory' message."""
        with pytest.raises(FileLoadError, match="directory"):
            load_history(tmp_path)

    def test_zero_byte_file_raises_file_load_error(self, tmp_path: Path) -> None:
        """A zero-byte history file raises FileLoadError with an 'empty' message."""
        p = tmp_path / "empty.json"
        p.write_bytes(b"")
        with pytest.raises(FileLoadError, match="empty"):
            load_history(p)

    def test_json_array_root_raises_data_validation_error(
        self, tmp_path: Path
    ) -> None:
        """A JSON array root (wrong schema) raises DataValidationError."""
        p = tmp_path / "array.json"
        _write_json(p, [1, 2, 3])
        with pytest.raises(DataValidationError):
            load_history(p)

    def test_json_null_root_raises_error(self, tmp_path: Path) -> None:
        """A JSON null root raises FileLoadError or DataValidationError."""
        p = tmp_path / "null.json"
        p.write_text("null", encoding="utf-8")
        with pytest.raises((FileLoadError, DataValidationError)):
            load_history(p)

    def test_invalid_json_raises_file_load_error(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text("{ not: valid json", encoding="utf-8")
        with pytest.raises(FileLoadError, match="JSON"):
            load_history(p)

    def test_asymmetric_matrix_raises_data_validation_error(
        self, tmp_path: Path
    ) -> None:
        p = tmp_path / "asym.json"
        _write_json(
            p,
            {
                "pair_counts": {
                    "Alice": {"Bob": 3},
                    "Bob": {"Alice": 1},  # asymmetric
                },
                "sit_out_counts": {},
            },
        )
        with pytest.raises(DataValidationError, match="[Aa]symmetric"):
            load_history(p)

    def test_negative_pair_count_raises_data_validation_error(
        self, tmp_path: Path
    ) -> None:
        p = tmp_path / "neg.json"
        _write_json(
            p,
            {
                "pair_counts": {
                    "Alice": {"Bob": -1},
                    "Bob": {"Alice": -1},
                },
                "sit_out_counts": {},
            },
        )
        with pytest.raises(DataValidationError):
            load_history(p)

    def test_negative_sit_out_count_raises_data_validation_error(
        self, tmp_path: Path
    ) -> None:
        p = tmp_path / "neg_sit.json"
        _write_json(p, {"pair_counts": {}, "sit_out_counts": {"Alice": -1}})
        with pytest.raises(DataValidationError):
            load_history(p)

    def test_empty_history_file_loads_as_empty(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.json"
        _write_json(p, {"pair_counts": {}, "sit_out_counts": {}})
        h = load_history(p)
        assert h.matrix == {}
        assert h.sit_out_counts == {}

    def test_version_field_ignored(self, tmp_path: Path) -> None:
        """Extra fields like 'version' are silently ignored."""
        p = tmp_path / "versioned.json"
        _write_json(
            p,
            {
                "version": "1",
                "pair_counts": {},
                "sit_out_counts": {},
            },
        )
        h = load_history(p)
        assert h.matrix == {}


class TestEmptyHistory:
    def test_returns_empty_pairing_history(self) -> None:
        h = empty_history()
        assert isinstance(h, PairingHistory)
        assert h.matrix == {}
        assert h.sit_out_counts == {}


class TestSaveHistory:
    def test_save_then_load_round_trip(self, tmp_path: Path) -> None:
        h = PairingHistory()
        h.increment_pair("Alice", "Bob")
        h.increment_pair("Alice", "Bob")
        h.increment_sit_out("Charlie")

        p = tmp_path / "history.json"
        save_history(h, p)

        loaded = load_history(p)
        assert loaded.get_pair_count("Alice", "Bob") == 2
        assert loaded.get_pair_count("Bob", "Alice") == 2
        assert loaded.sit_out_counts["Charlie"] == 1

    def test_atomic_write_temp_file_cleaned_up(self, tmp_path: Path) -> None:
        h = PairingHistory()
        p = tmp_path / "history.json"
        save_history(h, p)

        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_backup_created_on_overwrite(self, tmp_path: Path) -> None:
        h = PairingHistory()
        p = tmp_path / "history.json"
        save_history(h, p)
        h.increment_pair("A", "B")
        save_history(h, p)

        backup = Path(str(p) + ".backup")
        assert backup.exists()

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "history.json"
        h = PairingHistory()
        save_history(h, nested)
        assert nested.exists()

    def test_saved_json_is_valid(self, tmp_path: Path) -> None:
        h = PairingHistory()
        h.increment_pair("Alice", "Bob")
        p = tmp_path / "history.json"
        save_history(h, p)

        data = json.loads(p.read_text())
        assert "pair_counts" in data
        assert "sit_out_counts" in data


class TestPairingHistoryMutations:
    """Verify PairingHistory mutation helpers (complement to test_models.py)."""

    def test_prune_removes_stale_from_inner_dicts(self) -> None:
        h = PairingHistory()
        h.increment_pair("Alice", "Bob")
        h.increment_pair("Alice", "Charlie")
        h.prune({"Alice", "Bob"})

        assert "Charlie" not in h.matrix.get("Alice", {})
        assert "Charlie" not in h.sit_out_counts
