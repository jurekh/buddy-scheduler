"""Property-based fuzz tests for load_team_roster and load_history.

Safety contract under test: for every file content supplied to either loader,
the only observable outcomes are:

1. Return a valid result (list[TeamMember] or PairingHistory).
2. Raise FileLoadError.
3. Raise DataValidationError.

Any other exception type propagating out of a loader constitutes a test failure.

These tests are marked @pytest.mark.slow and excluded from the default pytest run.
Run them explicitly:

    uv run pytest tests/fuzz/ -m slow --hypothesis-seed=42 -v

The YAML safe-load enforcement tests (TestYamlSafeLoadEnforcement) are NOT marked
slow and always run in the default suite.
"""

from __future__ import annotations

import json
import textwrap
from datetime import timedelta
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from buddy_scheduler.cli import main
from buddy_scheduler.history import load_history
from buddy_scheduler.models import (
    DataValidationError,
    FileLoadError,
    PairingHistory,
    TeamMember,
)
from buddy_scheduler.validator import load_team_roster

# ---------------------------------------------------------------------------
# Shared settings
# ---------------------------------------------------------------------------

_SLOW_SETTINGS = settings(
    max_examples=100,
    deadline=timedelta(seconds=5),
    database=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)

_CLI_SETTINGS = settings(
    max_examples=50,
    deadline=timedelta(seconds=10),
    database=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)

# ---------------------------------------------------------------------------
# Pre-computed large inputs
# (st.text/st.binary with large min_size exceeds hypothesis's BUFFER_SIZE;
# use st.just() with pre-computed constants instead)
# ---------------------------------------------------------------------------

# >10 000 char text: valid YAML null comment → FileLoadError("empty")
_LARGE_YAML_TEXT: str = "# " + "x" * 9_999 + "\n"
# >10 000 char text: string value → FileLoadError("not a list")
_LARGE_STRING_VALUE: str = "x" * 10_001
# >1 MB non-UTF-8 binary → FileLoadError("invalid UTF-8")
_LARGE_BINARY_NON_UTF8: bytes = b"\x80" + b"x" * 1_048_575
# >1 MB valid JSON history object → validates successfully or DataValidationError
_LARGE_JSON_HISTORY: str = json.dumps(
    {"pair_counts": {}, "sit_out_counts": {}, "_pad": "x" * 900_000}
)

# ---------------------------------------------------------------------------
# Corpus strategies
# ---------------------------------------------------------------------------

_ROSTER_CORPUS = st.one_of(
    st.binary(),
    st.text(),
    st.just(""),
    st.just("null"),
    st.just("{}"),
    st.just("!!python/object/apply:os.system ['id']"),
    st.just("!!python/object/new:subprocess.Popen [['id']]"),
    st.just("!!python/tuple [1, 2, 3]"),
    st.just("!!python/name:os.getcwd"),
    st.just(_LARGE_YAML_TEXT),
    st.just(_LARGE_STRING_VALUE),
    st.just(_LARGE_BINARY_NON_UTF8),
    st.lists(
        st.fixed_dictionaries(
            {
                "name": st.text(min_size=0, max_size=64),
                "timezone": st.text(min_size=0, max_size=32),
                "active": st.booleans(),
                "avoid_buddies": st.lists(
                    st.text(min_size=1, max_size=20), max_size=5
                ),
            }
        ),
        min_size=0,
        max_size=10,
    ).map(yaml.safe_dump),
)

_HISTORY_CORPUS = st.one_of(
    st.binary(),
    st.text(),
    st.just(""),
    st.just("null"),
    st.just("[]"),
    st.just("{}"),
    st.just(_LARGE_YAML_TEXT),
    st.just(_LARGE_BINARY_NON_UTF8),
    st.just(_LARGE_JSON_HISTORY),
    st.recursive(
        st.none() | st.booleans() | st.integers() | st.text(),
        extend=lambda xs: st.lists(xs, max_size=3)
        | st.dictionaries(st.text(), xs, max_size=3),
        max_leaves=500,
    ).map(json.dumps),
    st.fixed_dictionaries(
        {
            "pair_counts": st.dictionaries(
                st.text(min_size=1),
                st.dictionaries(st.text(min_size=1), st.integers()),
            ),
            "sit_out_counts": st.dictionaries(st.text(min_size=1), st.integers()),
        }
    ).map(json.dumps),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_valid_team(path: Path) -> Path:
    """Write a fixed 4-member valid team YAML to *path* and return it."""
    path.write_text(
        textwrap.dedent(
            """\
            - name: Alice
              timezone: UTC
            - name: Bob
              timezone: UTC
            - name: Charlie
              timezone: UTC
            - name: Dave
              timezone: UTC
            """
        ),
        encoding="utf-8",
    )
    return path


def _write_content(path: Path, content: bytes | str) -> None:
    """Write *content* to *path*, handling both bytes and str."""
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8", errors="replace")


def _assert_safety_contract_team(path: Path) -> None:
    """Assert that load_team_roster raises only domain exceptions or succeeds."""
    try:
        result = load_team_roster(path)
        assert isinstance(result, list)
        assert all(isinstance(m, TeamMember) for m in result)
    except (FileLoadError, DataValidationError):
        pass
    except Exception as exc:
        pytest.fail(f"Unexpected {type(exc).__name__}: {exc}")


def _assert_safety_contract_history(path: Path) -> None:
    """Assert that load_history raises only domain exceptions or succeeds."""
    try:
        result = load_history(path)
        assert isinstance(result, PairingHistory)
    except (FileLoadError, DataValidationError):
        pass
    except Exception as exc:
        pytest.fail(f"Unexpected {type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# TestYamlSafeLoadEnforcement — deterministic, NOT marked slow
# ---------------------------------------------------------------------------


_PYTHON_YAML_TAGS = [
    "!!python/object/apply:os.system ['id']",
    "!!python/object/new:subprocess.Popen [['id']]",
    "!!python/tuple [1, 2, 3]",
    "!!python/name:os.getcwd",
]


class TestJsonRecursionSafety:
    """Verify load_history raises FileLoadError for deeply nested JSON.

    Python's json.loads is a recursive parser; inputs near the recursion limit
    raise RecursionError, not JSONDecodeError.  This must be caught and converted
    to FileLoadError to uphold the safety contract.

    Not marked slow — deterministic single example.
    """

    def test_deeply_nested_json_raises_file_load_error(
        self, tmp_path: Path
    ) -> None:
        """Deeply nested JSON raises FileLoadError, not RecursionError."""
        import sys

        depth = sys.getrecursionlimit() + 100
        nested: str = ("{" * depth) + ("}" * depth)
        p = tmp_path / "history.json"
        p.write_text(nested, encoding="utf-8")
        with pytest.raises(FileLoadError):
            load_history(p)


class TestYamlSafeLoadEnforcement:
    """Verify yaml.safe_load is enforced: Python-specific YAML tags are rejected.

    These tests are fast and security-critical; they run in the default test suite
    (no @pytest.mark.slow marker) per FR-006.
    """

    @pytest.mark.parametrize("tag_content", _PYTHON_YAML_TAGS)
    def test_python_tag_is_rejected(
        self, tmp_path: Path, tag_content: str
    ) -> None:
        """A YAML file containing a Python-specific tag raises FileLoadError."""
        p = tmp_path / "team.yaml"
        p.write_text(tag_content, encoding="utf-8")
        with pytest.raises(FileLoadError):
            load_team_roster(p)


# ---------------------------------------------------------------------------
# TestFuzzTeamRoster — fuzz tests for load_team_roster
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestFuzzTeamRoster:
    """Safety-contract fuzz tests for load_team_roster.

    For every generated input, the loader must either return list[TeamMember]
    or raise FileLoadError / DataValidationError.  Any other exception is a failure.
    """

    @given(content=st.binary())
    @_SLOW_SETTINGS
    def test_arbitrary_bytes_safety_contract(
        self, tmp_path: Path, content: bytes
    ) -> None:
        """Any byte sequence either returns a valid roster or raises a domain error."""
        p = tmp_path / "team.yaml"
        p.write_bytes(content)
        _assert_safety_contract_team(p)

    @given(content=_ROSTER_CORPUS)
    @_SLOW_SETTINGS
    def test_structured_yaml_safety_contract(
        self, tmp_path: Path, content: bytes | str
    ) -> None:
        """Full corpus (random + structured YAML) never raises unexpected exceptions."""
        p = tmp_path / "team.yaml"
        _write_content(p, content)
        _assert_safety_contract_team(p)


# ---------------------------------------------------------------------------
# TestFuzzHistory — fuzz tests for load_history
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestFuzzHistory:
    """Safety-contract fuzz tests for load_history.

    For every generated input, the loader must either return PairingHistory
    or raise FileLoadError / DataValidationError.  Any other exception is a failure.
    """

    @given(content=st.binary())
    @_SLOW_SETTINGS
    def test_arbitrary_bytes_safety_contract(
        self, tmp_path: Path, content: bytes
    ) -> None:
        """Any byte sequence either returns valid history or raises a domain error."""
        p = tmp_path / "history.json"
        p.write_bytes(content)
        _assert_safety_contract_history(p)

    @given(content=_HISTORY_CORPUS)
    @_SLOW_SETTINGS
    def test_structured_json_safety_contract(
        self, tmp_path: Path, content: bytes | str
    ) -> None:
        """Full corpus (random + structured JSON) never raises unexpected exceptions."""
        p = tmp_path / "history.json"
        _write_content(p, content)
        _assert_safety_contract_history(p)


# ---------------------------------------------------------------------------
# TestFuzzCLI — fuzz tests for the CLI exit-code contract
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestFuzzCLI:
    """Fuzz tests for the CLI exit-code contract.

    For any file content supplied as --team or --history, the CLI must exit with
    code 0 or 1.  On non-zero exit, stdout must parse as JSON with
    {"success": false, "error": ...}.
    """

    @given(content=st.binary())
    @_CLI_SETTINGS
    def test_team_file_content_exits_zero_or_one(
        self, tmp_path: Path, content: bytes
    ) -> None:
        """Any --team file content produces exit code 0 or 1."""
        team_path = tmp_path / "fuzz_team.yaml"
        team_path.write_bytes(content)
        runner = CliRunner()
        result = runner.invoke(main, ["--team", str(team_path)])
        assert result.exit_code in (0, 1), (
            f"Unexpected exit_code={result.exit_code}: {result.output!r}"
        )
        if result.exit_code != 0:
            data = json.loads(result.stdout)
            assert data["success"] is False
            assert "error" in data

    @given(content=st.binary())
    @_CLI_SETTINGS
    def test_history_file_content_exits_zero_or_one(
        self, tmp_path: Path, content: bytes
    ) -> None:
        """Any --history file content (with a valid team) produces exit code 0 or 1."""
        team_path = _write_valid_team(tmp_path / "team.yaml")
        history_path = tmp_path / "fuzz_history.json"
        history_path.write_bytes(content)
        runner = CliRunner()
        result = runner.invoke(
            main, ["--team", str(team_path), "--history", str(history_path)]
        )
        assert result.exit_code in (0, 1), (
            f"Unexpected exit_code={result.exit_code}: {result.output!r}"
        )
        if result.exit_code != 0:
            data = json.loads(result.stdout)
            assert data["success"] is False
            assert "error" in data
