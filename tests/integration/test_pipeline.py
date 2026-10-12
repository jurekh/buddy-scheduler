"""Integration tests for the full buddy-scheduler pipeline."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from click.testing import CliRunner

from buddy_scheduler.cli import main


def _write_yaml(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


def _run(tmp_path: Path, *args: str) -> tuple[int, dict]:  # type: ignore[type-arg]
    runner = CliRunner()
    result = runner.invoke(main, list(args))
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        data = {"_raw": result.stdout}
    return result.exit_code, data


class TestBasicPipeline:
    def test_even_n_team_succeeds(self, tmp_path: Path) -> None:
        p = _write_yaml(
            tmp_path,
            "team.yaml",
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
        code, data = _run(tmp_path, "--team", str(p))

        assert code == 0
        assert data["success"] is True
        assert len(data["pairs"]) == 2
        assert data["sitting_out"] is None

    def test_odd_n_team_has_sit_out(self, tmp_path: Path) -> None:
        p = _write_yaml(
            tmp_path,
            "team.yaml",
            """
            - name: Alice
              timezone: UTC
            - name: Bob
              timezone: UTC
            - name: Charlie
              timezone: UTC
            """,
        )
        code, data = _run(tmp_path, "--team", str(p))

        assert code == 0
        assert data["success"] is True
        assert len(data["pairs"]) == 1
        assert data["sitting_out"] is not None
        assert data["sitting_out"] in {"Alice", "Bob", "Charlie"}

    def test_inactive_member_excluded(self, tmp_path: Path) -> None:
        p = _write_yaml(
            tmp_path,
            "team.yaml",
            """
            - name: Alice
              timezone: UTC
            - name: Bob
              timezone: UTC
            - name: Charlie
              timezone: UTC
              active: false
            - name: Dave
              timezone: UTC
            """,
        )
        code, data = _run(tmp_path, "--team", str(p))

        assert code == 0
        all_names = {name for pair in data["pairs"] for name in pair}
        assert "Charlie" not in all_names
        assert data.get("inactive_members") == ["Charlie"]


class TestHistoryPipeline:
    def test_two_sequential_runs_produce_different_pairings(
        self, tmp_path: Path
    ) -> None:
        p = _write_yaml(
            tmp_path,
            "team.yaml",
            """
            - name: Alice
              timezone: UTC
            - name: Bob
              timezone: UTC
            - name: Charlie
              timezone: UTC
            - name: Dave
              timezone: UTC
            - name: Eve
              timezone: UTC
            - name: Frank
              timezone: UTC
            """,
        )
        history_path = tmp_path / "h.json"

        _, data1 = _run(
            tmp_path,
            "--team",
            str(p),
            "--history",
            str(history_path),
            "--update-history",
        )
        _, data2 = _run(
            tmp_path,
            "--team",
            str(p),
            "--history",
            str(history_path),
            "--update-history",
        )

        pairs1 = {frozenset(pair) for pair in data1["pairs"]}
        pairs2 = {frozenset(pair) for pair in data2["pairs"]}
        # With 6 members and history weighting, the second run should differ
        assert pairs1 != pairs2

    def test_prune_history_removes_stale_members(self, tmp_path: Path) -> None:
        history_path = tmp_path / "h.json"
        # Seed history with a member who is no longer in the roster
        history_data = {
            "pair_counts": {
                "Alice": {"Ghost": 1, "Bob": 1},
                "Ghost": {"Alice": 1},
                "Bob": {"Alice": 1},
            },
            "sit_out_counts": {"Ghost": 2},
        }
        history_path.write_text(json.dumps(history_data), encoding="utf-8")

        p = _write_yaml(
            tmp_path,
            "team.yaml",
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
        code, _ = _run(
            tmp_path,
            "--team",
            str(p),
            "--history",
            str(history_path),
            "--update-history",
            "--prune-history",
        )
        assert code == 0

        updated = json.loads(history_path.read_text())
        assert "Ghost" not in updated["pair_counts"]
        assert "Ghost" not in updated.get("sit_out_counts", {})


class TestErrorHandling:
    def test_avoidance_infeasibility_exits_one(self, tmp_path: Path) -> None:
        p = _write_yaml(
            tmp_path,
            "team.yaml",
            """
            - name: Alice
              timezone: UTC
              avoid_buddies: [Bob, Charlie, Dave]
            - name: Bob
              timezone: UTC
            - name: Charlie
              timezone: UTC
            - name: Dave
              timezone: UTC
            """,
        )
        code, data = _run(tmp_path, "--team", str(p))

        assert code == 1
        assert data["success"] is False
        assert "avoidance_conflicts" in data

    def test_malformed_yaml_exits_one(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.yaml"
        p.write_text("{ bad yaml ][", encoding="utf-8")
        code, data = _run(tmp_path, "--team", str(p))

        assert code == 1
        assert data["success"] is False
        assert "error" in data

    def test_missing_team_file_exits_one(self, tmp_path: Path) -> None:
        code, data = _run(tmp_path, "--team", str(tmp_path / "nope.yaml"))

        assert code == 1
        assert data["success"] is False

    def test_update_history_without_explicit_path_creates_file(
        self, tmp_path: Path
    ) -> None:
        p = _write_yaml(
            tmp_path,
            "myteam.yaml",
            """
            - name: Alice
              timezone: UTC
            - name: Bob
              timezone: UTC
            """,
        )
        code, data = _run(tmp_path, "--team", str(p), "--update-history")

        assert code == 0
        inferred = tmp_path / "myteam.history.json"
        assert inferred.exists()
        assert data["history_updated"] is True
