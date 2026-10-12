"""History store: load, save, and empty-factory for PairingHistory."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout
from pydantic import BaseModel, ConfigDict, field_validator

from buddy_scheduler.models import (
    DataValidationError,
    FileLoadError,
    FileSaveError,
    PairingHistory,
)

logger = logging.getLogger(__name__)


class _HistoryModel(BaseModel):
    """Pydantic model for on-disk history JSON validation."""

    model_config = ConfigDict(extra="ignore")

    pair_counts: dict[str, dict[str, int]] = {}
    sit_out_counts: dict[str, int] = {}

    @field_validator("pair_counts")
    @classmethod
    def check_symmetry(
        cls, v: dict[str, dict[str, int]]
    ) -> dict[str, dict[str, int]]:
        """Verify the pair_counts matrix is symmetric."""
        for a, row in v.items():
            for b, count in row.items():
                reverse = v.get(b, {}).get(a)
                if reverse is None or reverse != count:
                    raise ValueError(
                        f"Asymmetric history matrix: {a}↔{b} "
                        f"({count} vs {reverse})"
                    )
        return v

    @field_validator("pair_counts")
    @classmethod
    def check_non_negative_pairs(
        cls, v: dict[str, dict[str, int]]
    ) -> dict[str, dict[str, int]]:
        """Verify all pair counts are non-negative."""
        for a, row in v.items():
            for b, count in row.items():
                if count < 0:
                    raise ValueError(
                        f"Negative pair count for {a}↔{b}: {count}"
                    )
        return v

    @field_validator("sit_out_counts")
    @classmethod
    def check_non_negative_sit_outs(
        cls, v: dict[str, int]
    ) -> dict[str, int]:
        """Verify all sit-out counts are non-negative."""
        for name, count in v.items():
            if count < 0:
                raise ValueError(f"Negative sit-out count for {name}: {count}")
        return v


def _model_to_history(model: _HistoryModel) -> PairingHistory:
    """Convert a validated Pydantic model to a PairingHistory dataclass."""
    return PairingHistory(
        matrix=model.pair_counts,
        sit_out_counts=model.sit_out_counts,
    )


def load_history(path: Path) -> PairingHistory:
    """Load and validate a pairing history from a JSON file.

    Args:
        path: Path to the JSON history store file.

    Returns:
        A validated PairingHistory instance.

    Raises:
        FileLoadError: If the file is missing or not valid JSON.
        DataValidationError: If the history fails structural validation
            (asymmetric matrix, negative counts).
    """
    try:
        exists = path.exists()
    except OSError as exc:
        raise FileLoadError(
            f"Cannot access history file {path}: {exc}"
        ) from exc

    if not exists:
        raise FileLoadError(f"History file not found: {path}")

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FileLoadError(f"Cannot read history file {path}: {exc}") from exc

    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FileLoadError(
            f"History file is not valid JSON: {exc}"
        ) from exc

    try:
        model = _HistoryModel.model_validate(data)
    except Exception as exc:
        raise DataValidationError(
            f"History validation failed: {exc}"
        ) from exc

    history = _model_to_history(model)
    logger.info(
        "Loaded history for %d members from %s",
        len(history.matrix),
        path,
    )
    return history


def empty_history() -> PairingHistory:
    """Return an empty PairingHistory with no prior pairings."""
    return PairingHistory()


def save_history(history: PairingHistory, path: Path) -> None:
    """Write a PairingHistory atomically to a JSON file.

    The write is:
    1. Serialised via ``FileLock`` to prevent concurrent writes.
    2. Written to a temporary file in the same directory.
    3. fsynced before rename.
    4. The existing file is backed up to ``{path}.backup`` before overwrite.
    5. Renamed atomically with ``os.replace``.

    Args:
        history: The PairingHistory to persist.
        path: Destination path for the JSON file.

    Raises:
        FileSaveError: On any I/O error or lock timeout.
    """
    lock_path = str(path) + ".lock"
    payload = {
        "pair_counts": history.matrix,
        "sit_out_counts": history.sit_out_counts,
    }

    try:
        with FileLock(lock_path, timeout=10):
            # Write to a temp file in the same directory for atomic rename
            dir_path = path.parent
            dir_path.mkdir(parents=True, exist_ok=True)

            tmp_fd, tmp_path = tempfile.mkstemp(
                dir=dir_path, suffix=".tmp"
            )
            try:
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2, sort_keys=True)
                    f.flush()
                    os.fsync(f.fileno())
            except OSError:
                import contextlib

                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)
                raise

            # Backup existing file before overwrite
            if path.exists():
                backup = str(path) + ".backup"
                os.replace(str(path), backup)

            os.replace(tmp_path, str(path))

    except Timeout as exc:
        raise FileSaveError(
            f"Could not acquire lock for {path} within 10 seconds"
        ) from exc
    except OSError as exc:
        raise FileSaveError(f"Failed to write history to {path}: {exc}") from exc

    logger.info("Saved history to %s", path)
