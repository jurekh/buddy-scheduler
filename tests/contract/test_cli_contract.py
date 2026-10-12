"""Contract tests for CLI JSON output schema, exit codes, and stream routing."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner

from buddy_scheduler.cli import main
from buddy_scheduler.models import OptimizationError


def _write_team(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "team.yaml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


def _valid_team(tmp_path: Path) -> Path:
    return _write_team(
        tmp_path,
        """
        - name: Alice
          timezone: UTC
        - name: Bob
          timezone: UTC
        - name: Charlie
          timezone: UTC
        - name: Dave
          timezone: UTC
        """,
    )


def _parse(stdout: str) -> dict:  # type: ignore[type-arg]
    return json.loads(stdout)


class TestExitCodes:
    def test_valid_team_exits_zero(self, tmp_path: Path) -> None:
        runner = CliRunner()
        p = _valid_team(tmp_path)
        result = runner.invoke(main, ["--team", str(p)])
        assert result.exit_code == 0

    def test_missing_team_option_exits_nonzero(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, [])
        assert result.exit_code != 0

    def test_nonexistent_team_file_exits_one(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--team", str(tmp_path / "nope.yaml")])
        assert result.exit_code == 1

    def test_invalid_log_level_exits_one(self, tmp_path: Path) -> None:
        p = _valid_team(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["--team", str(p), "--log-level", "VERBOSE"])
        assert result.exit_code == 1

    def test_unknown_solver_profile_exits_one(self, tmp_path: Path) -> None:
        p = _valid_team(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["--team", str(p), "--solver-profile", "turbo"])
        assert result.exit_code == 1

    def test_team_directory_exits_one(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--team", str(tmp_path)])
        assert result.exit_code == 1
        data = _parse(result.stdout)
        assert data["success"] is False
        assert "error" in data

    def test_history_weight_zero_exits_zero(self, tmp_path: Path) -> None:
        p = _valid_team(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["--team", str(p), "--history-weight", "0.0"])
        assert result.exit_code == 0
        data = _parse(result.stdout)
        assert data["success"] is True

    def test_tz_weight_zero_exits_zero(self, tmp_path: Path) -> None:
        p = _valid_team(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["--team", str(p), "--tz-weight", "0.0"])
        assert result.exit_code == 0
        data = _parse(result.stdout)
        assert data["success"] is True

    def test_history_weight_non_numeric_exits_nonzero(self, tmp_path: Path) -> None:
        p = _valid_team(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["--team", str(p), "--history-weight", "high"])
        assert result.exit_code != 0

    def test_tz_weight_non_numeric_exits_nonzero(self, tmp_path: Path) -> None:
        p = _valid_team(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["--team", str(p), "--tz-weight", "medium"])
        assert result.exit_code != 0

    def test_negative_history_weight_exits_one(self, tmp_path: Path) -> None:
        p = _valid_team(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["--team", str(p), "--history-weight", "-1.0"])
        assert result.exit_code == 1

    def test_negative_tz_weight_exits_one(self, tmp_path: Path) -> None:
        p = _valid_team(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["--team", str(p), "--tz-weight", "-0.5"])
        assert result.exit_code == 1

    def test_solver_failure_exits_two(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import buddy_scheduler.solver.mip as mip_module

        def _raise(*args: object, **kwargs: object) -> None:
            raise OptimizationError("all strategies exhausted")

        monkeypatch.setattr(mip_module, "solve_pairing", _raise)
        p = _valid_team(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["--team", str(p)])
        assert result.exit_code == 2
        data = _parse(result.stdout)
        assert data["success"] is False


class TestJsonOutputSchema:
    def test_success_has_required_keys(self, tmp_path: Path) -> None:
        runner = CliRunner()
        p = _valid_team(tmp_path)
        result = runner.invoke(main, ["--team", str(p)])

        data = _parse(result.stdout)
        for key in [
            "success",
            "pairs",
            "sitting_out",
            "optimization_score",
            "solve_time",
            "solver_profile",
            "history_updated",
        ]:
            assert key in data, f"Missing key: {key}"

    def test_success_field_is_true(self, tmp_path: Path) -> None:
        runner = CliRunner()
        p = _valid_team(tmp_path)
        result = runner.invoke(main, ["--team", str(p)])

        data = _parse(result.stdout)
        assert data["success"] is True

    def test_pairs_sorted_within_and_across(self, tmp_path: Path) -> None:
        runner = CliRunner()
        p = _valid_team(tmp_path)
        result = runner.invoke(main, ["--team", str(p)])

        data = _parse(result.stdout)
        pairs = data["pairs"]
        for pair in pairs:
            assert pair == sorted(pair), "Pair not sorted internally"
        assert pairs == sorted(pairs, key=lambda p: p[0]), "Pairs not sorted"

    def test_failure_json_on_nonexistent_file(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--team", str(tmp_path / "nope.yaml")])

        data = _parse(result.stdout)
        assert data["success"] is False
        assert "error" in data

    def test_stdout_contains_valid_json_only(self, tmp_path: Path) -> None:
        runner = CliRunner()
        p = _valid_team(tmp_path)
        result = runner.invoke(main, ["--team", str(p), "--log-level", "DEBUG"])

        # stdout should be pure JSON; stderr has logs
        data = _parse(result.stdout)
        assert isinstance(data, dict)

    def test_log_lines_not_in_stdout(self, tmp_path: Path) -> None:
        runner = CliRunner()
        p = _valid_team(tmp_path)
        result = runner.invoke(main, ["--team", str(p), "--log-level", "DEBUG"])

        # stdout is pure JSON — no log level markers
        assert "[INFO]" not in result.stdout
        assert "[DEBUG]" not in result.stdout


class TestStreamRouting:
    def test_stdout_is_valid_json(self, tmp_path: Path) -> None:
        runner = CliRunner()
        p = _valid_team(tmp_path)
        result = runner.invoke(main, ["--team", str(p)])

        # Should not raise
        json.loads(result.stdout)

    def test_all_active_members_in_pairs(self, tmp_path: Path) -> None:
        runner = CliRunner()
        p = _valid_team(tmp_path)
        result = runner.invoke(main, ["--team", str(p)])

        data = _parse(result.stdout)
        all_paired = {name for pair in data["pairs"] for name in pair}
        assert all_paired == {"Alice", "Bob", "Charlie", "Dave"}


class TestHistoryFlags:
    def test_update_history_creates_file(self, tmp_path: Path) -> None:
        p = _valid_team(tmp_path)
        history_path = tmp_path / "h.json"
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--team", str(p), "--history", str(history_path), "--update-history"],
        )

        assert result.exit_code == 0
        assert history_path.exists()
        data = json.loads(history_path.read_text())
        assert "pair_counts" in data

    def test_update_history_flag_set_in_result(self, tmp_path: Path) -> None:
        p = _valid_team(tmp_path)
        history_path = tmp_path / "h.json"
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--team", str(p), "--history", str(history_path), "--update-history"],
        )

        data = _parse(result.stdout)
        assert data["history_updated"] is True

    def test_without_update_history_no_file_created(self, tmp_path: Path) -> None:
        p = _valid_team(tmp_path)
        history_path = tmp_path / "h.json"
        runner = CliRunner()
        runner.invoke(main, ["--team", str(p)])

        assert not history_path.exists()

    def test_prune_without_update_history_exit_zero(self, tmp_path: Path) -> None:
        """--prune-history without --update-history is silently ignored."""
        p = _valid_team(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["--team", str(p), "--prune-history"])

        assert result.exit_code == 0

    def test_update_history_without_explicit_path_auto_creates(
        self, tmp_path: Path
    ) -> None:
        p = _valid_team(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["--team", str(p), "--update-history"])

        assert result.exit_code == 0
        inferred = tmp_path / "team.history.json"
        assert inferred.exists()

    def test_history_directory_exits_one(self, tmp_path: Path) -> None:
        p = _valid_team(tmp_path)
        history_dir = tmp_path / "histdir"
        history_dir.mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["--team", str(p), "--history", str(history_dir)])
        assert result.exit_code == 1
        data = _parse(result.stdout)
        assert data["success"] is False
        assert "error" in data

    def test_history_non_json_exits_one(self, tmp_path: Path) -> None:
        p = _valid_team(tmp_path)
        bad_history = tmp_path / "bad.json"
        bad_history.write_text("not json at all", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(main, ["--team", str(p), "--history", str(bad_history)])
        assert result.exit_code == 1
        data = _parse(result.stdout)
        assert data["success"] is False
        assert "error" in data
