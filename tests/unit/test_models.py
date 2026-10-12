"""Unit tests for models, exceptions, and OptimizationResult serialization."""

from __future__ import annotations

import pytest

from buddy_scheduler.models import (
    BuddySchedulerError,
    DataValidationError,
    FileLoadError,
    FileSaveError,
    OptimizationError,
    OptimizationResult,
    PairingHistory,
    TeamMember,
)


class TestExceptionHierarchy:
    """Verify the exception class hierarchy and message propagation."""

    def test_all_subclasses_are_buddy_scheduler_error(self) -> None:
        for cls in [
            FileLoadError,
            FileSaveError,
            DataValidationError,
            OptimizationError,
        ]:
            exc = cls("msg")
            assert isinstance(exc, BuddySchedulerError)
            assert isinstance(exc, Exception)

    def test_message_preserved(self) -> None:
        exc = FileLoadError("file not found")
        assert exc.message == "file not found"
        assert str(exc) == "file not found"

    def test_subclasses_are_distinct(self) -> None:
        assert not isinstance(FileLoadError("x"), DataValidationError)
        assert not isinstance(DataValidationError("x"), FileSaveError)

    def test_base_not_catchable_as_stdlib_exception_only(self) -> None:
        with pytest.raises(BuddySchedulerError):
            raise OptimizationError("exhausted")


class TestTeamMember:
    """Verify TeamMember defaults and field independence."""

    def test_defaults(self) -> None:
        m = TeamMember(name="Alice", timezone="UTC+0")
        assert m.active is True
        assert m.avoid_buddies == []

    def test_custom_values(self) -> None:
        m = TeamMember(
            name="Bob",
            timezone="America/New_York",
            active=False,
            avoid_buddies=["Alice"],
        )
        assert m.active is False
        assert m.avoid_buddies == ["Alice"]

    def test_avoid_buddies_default_is_independent_per_instance(self) -> None:
        m1 = TeamMember(name="A", timezone="UTC")
        m2 = TeamMember(name="B", timezone="UTC")
        m1.avoid_buddies.append("X")
        assert m2.avoid_buddies == []


class TestPairingHistory:
    """Verify PairingHistory mutation helpers and prune."""

    def test_get_pair_count_missing_returns_zero(self) -> None:
        h = PairingHistory()
        assert h.get_pair_count("Alice", "Bob") == 0

    def test_increment_pair_is_symmetric(self) -> None:
        h = PairingHistory()
        h.increment_pair("Alice", "Bob")
        assert h.get_pair_count("Alice", "Bob") == 1
        assert h.get_pair_count("Bob", "Alice") == 1

    def test_increment_pair_accumulates(self) -> None:
        h = PairingHistory()
        h.increment_pair("A", "B")
        h.increment_pair("A", "B")
        assert h.get_pair_count("A", "B") == 2

    def test_increment_sit_out(self) -> None:
        h = PairingHistory()
        h.increment_sit_out("Alice")
        assert h.sit_out_counts["Alice"] == 1
        h.increment_sit_out("Alice")
        assert h.sit_out_counts["Alice"] == 2

    def test_prune_removes_absent_members(self) -> None:
        h = PairingHistory()
        h.increment_pair("Alice", "Bob")
        h.increment_pair("Alice", "Charlie")
        h.increment_sit_out("Charlie")
        h.prune({"Alice", "Bob"})
        assert "Charlie" not in h.matrix
        assert "Charlie" not in h.sit_out_counts
        assert "Charlie" not in h.matrix.get("Alice", {})

    def test_prune_keeps_active_members(self) -> None:
        h = PairingHistory()
        h.increment_pair("Alice", "Bob")
        h.prune({"Alice", "Bob"})
        assert h.get_pair_count("Alice", "Bob") == 1


class TestOptimizationResult:
    """Verify OptimizationResult.to_dict() serialization."""

    def _make_result(self, **kwargs: object) -> OptimizationResult:
        defaults: dict[str, object] = {
            "success": True,
            "pairs": [("Alice", "Bob")],
            "sitting_out": None,
            "optimization_score": 1.5,
            "solve_time": 0.42,
            "solver_profile": "balanced",
        }
        defaults.update(kwargs)
        return OptimizationResult(**defaults)  # type: ignore[arg-type]

    def test_required_keys_present(self) -> None:
        d = self._make_result().to_dict()
        for key in [
            "success",
            "pairs",
            "sitting_out",
            "optimization_score",
            "solve_time",
            "solver_profile",
            "history_updated",
        ]:
            assert key in d, f"Missing key: {key}"

    def test_none_optional_fields_omitted(self) -> None:
        d = self._make_result().to_dict()
        for key in ["solver_gap", "peak_memory_mb", "memory_delta_mb", "error"]:
            assert key not in d, f"Unexpected key: {key}"

    def test_solver_gap_included_when_set(self) -> None:
        d = self._make_result(solver_gap=0.001).to_dict()
        assert d["solver_gap"] == 0.001

    def test_pairs_sorted_within_pair(self) -> None:
        d = self._make_result(pairs=[("Zelda", "Alice")]).to_dict()
        assert d["pairs"] == [["Alice", "Zelda"]]

    def test_pairs_sorted_across_pairs(self) -> None:
        d = self._make_result(pairs=[("Zelda", "Yuki"), ("Alice", "Bob")]).to_dict()
        assert d["pairs"][0][0] < d["pairs"][1][0]

    def test_empty_lists_omitted(self) -> None:
        d = self._make_result().to_dict()
        assert "inactive_members" not in d
        assert "avoidance_conflicts" not in d

    def test_non_empty_lists_included(self) -> None:
        d = self._make_result(
            inactive_members=["Eve"],
            avoidance_conflicts=["A↔B"],
        ).to_dict()
        assert d["inactive_members"] == ["Eve"]
        assert d["avoidance_conflicts"] == ["A↔B"]

    def test_error_field_included_when_set(self) -> None:
        d = self._make_result(error="something went wrong").to_dict()
        assert d["error"] == "something went wrong"
