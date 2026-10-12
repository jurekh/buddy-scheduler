"""Doc-driven test framework: extracts and executes annotated examples from docs."""

from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass
from pathlib import Path

import click
import pytest
import yaml
from click.testing import CliRunner

from buddy_scheduler.cli import main
from buddy_scheduler.models import DataValidationError
from buddy_scheduler.validator import load_team_roster

DOCS_DIR = Path(__file__).parent.parent.parent / "docs"
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

REQUIRED_SUCCESS_FIELDS: frozenset[str] = frozenset(
    {
        "success",
        "pairs",
        "sitting_out",
        "optimization_score",
        "solve_time",
        "solver_profile",
        "history_updated",
    }
)

_ANNOTATION_RE = re.compile(
    r"<!--\s*test:\s+(?P<kind>cli|yaml)\s*(?P<params>.*?)\s*-->"
)
_FIXTURE_RE = re.compile(r"fixture=(\S+)")
_EXIT_RE = re.compile(r"exit=(\d+)")

_DOCS_WITH_REQUIRED_ANNOTATIONS = [
    "tutorial/getting-started.md",
    "how-to/track-history.md",
    "how-to/manage-absences.md",
    "how-to/avoid-pairings.md",
    "reference/cli.md",
    "reference/output-format.md",
    "reference/team-yaml.md",
]


@dataclass(frozen=True)
class DocExample:
    doc_path: Path
    line_no: int
    kind: str  # "cli", "yaml-match", "yaml-validate"
    fixture: str | None
    exit_code: int
    content: str

    @property
    def test_id(self) -> str:
        rel = self.doc_path.relative_to(DOCS_DIR)
        return f"{rel}:{self.line_no}"


def _parse_file(doc_path: Path) -> list[DocExample]:
    lines = doc_path.read_text(encoding="utf-8").splitlines()
    examples: list[DocExample] = []
    i = 0
    while i < len(lines):
        m = _ANNOTATION_RE.fullmatch(lines[i].strip())
        if m and i + 1 < len(lines) and lines[i + 1].startswith("```"):
            annotation_line_no = i + 1  # 1-indexed
            kind_raw = m.group("kind")
            params = m.group("params")

            fixture_m = _FIXTURE_RE.search(params)
            fixture = fixture_m.group(1) if fixture_m else None
            exit_m = _EXIT_RE.search(params)
            exit_code = int(exit_m.group(1)) if exit_m else 0

            if kind_raw == "yaml" and fixture:
                kind = "yaml-match"
            elif kind_raw == "yaml":
                kind = "yaml-validate"
            else:
                kind = "cli"

            # Advance past the opening fence line
            i += 2
            content_lines: list[str] = []
            while i < len(lines) and not lines[i].startswith("```"):
                content_lines.append(lines[i])
                i += 1
            # Skip the closing fence
            if i < len(lines):
                i += 1

            examples.append(
                DocExample(
                    doc_path=doc_path,
                    line_no=annotation_line_no,
                    kind=kind,
                    fixture=fixture,
                    exit_code=exit_code,
                    content="\n".join(content_lines),
                )
            )
        else:
            i += 1
    return examples


def collect_doc_examples() -> list[DocExample]:
    if not DOCS_DIR.exists():
        return []
    examples: list[DocExample] = []
    for md_file in sorted(DOCS_DIR.rglob("*.md")):
        examples.extend(_parse_file(md_file))
    return examples


_ALL_EXAMPLES = collect_doc_examples()


def _run_cli_example(example: DocExample, tmp_path: Path) -> None:
    loc = f"{example.doc_path}:{example.line_no}"

    # Find first line containing "buddy-scheduler"
    cmd_line: str | None = None
    for line in example.content.splitlines():
        stripped = line.strip()
        if stripped.startswith("buddy-scheduler"):
            cmd_line = stripped
            break
    assert cmd_line is not None, f"{loc}: no buddy-scheduler command found in block"

    # Strip inline comments
    cmd_line = re.sub(r"\s+#.*$", "", cmd_line)

    args = shlex.split(cmd_line)[1:]  # drop "buddy-scheduler"

    # Substitute --team value with fixture path
    if example.fixture:
        fixture_src = FIXTURES_DIR / example.fixture
        dest = tmp_path / "team.yaml"
        dest.write_bytes(fixture_src.read_bytes())
        new_args: list[str] = []
        j = 0
        while j < len(args):
            if args[j] == "--team" and j + 1 < len(args):
                new_args += ["--team", str(dest)]
                j += 2
            else:
                new_args.append(args[j])
                j += 1
        args = new_args

    # Substitute --history value path to tmp_path
    new_args2: list[str] = []
    k = 0
    while k < len(args):
        if args[k] == "--history" and k + 1 < len(args):
            hist_name = Path(args[k + 1]).name
            new_args2 += ["--history", str(tmp_path / hist_name)]
            k += 2
        else:
            new_args2.append(args[k])
            k += 1
    args = new_args2

    runner = CliRunner()
    result = runner.invoke(main, args)

    assert result.exit_code == example.exit_code, (
        f"{loc}: expected exit {example.exit_code}, "
        f"got {result.exit_code}.\nOutput: {result.output}"
    )

    if example.exit_code == 0:
        try:
            data = json.loads(result.output)
        except json.JSONDecodeError as exc:
            pytest.fail(f"{loc}: output is not valid JSON: {exc}\n{result.output}")
        missing = REQUIRED_SUCCESS_FIELDS - data.keys()
        assert not missing, (
            f"{loc}: success output missing required fields: {missing}"
        )


def _run_yaml_match(example: DocExample) -> None:
    loc = f"{example.doc_path}:{example.line_no}"
    assert example.fixture is not None
    fixture_path = FIXTURES_DIR / example.fixture
    assert fixture_path.exists(), (
        f"{loc}: fixture file not found: {fixture_path}"
    )
    actual = fixture_path.read_text(encoding="utf-8").strip()
    expected = example.content.strip()
    assert expected == actual, (
        f"{loc}: doc YAML block does not match fixture {example.fixture}.\n"
        f"--- fixture ---\n{actual}\n--- doc block ---\n{expected}"
    )


def _run_yaml_validate(example: DocExample, tmp_path: Path) -> None:
    loc = f"{example.doc_path}:{example.line_no}"
    tmp_file = tmp_path / "roster.yaml"
    tmp_file.write_text(example.content, encoding="utf-8")

    if example.exit_code == 0:
        try:
            load_team_roster(tmp_file)
        except Exception as exc:
            pytest.fail(f"{loc}: expected valid YAML but got error: {exc}")
    else:
        with pytest.raises(
            (DataValidationError, Exception),
            match=r".*",
        ):
            load_team_roster(tmp_file)


@pytest.mark.parametrize(
    "example",
    _ALL_EXAMPLES,
    ids=[e.test_id for e in _ALL_EXAMPLES],
)
def test_doc_example(example: DocExample, tmp_path: Path) -> None:
    if example.kind == "cli":
        _run_cli_example(example, tmp_path)
    elif example.kind == "yaml-match":
        _run_yaml_match(example)
    elif example.kind == "yaml-validate":
        _run_yaml_validate(example, tmp_path)
    else:
        pytest.fail(f"Unknown example kind: {example.kind!r}")


def test_all_docs_have_annotated_examples() -> None:
    annotated_docs: set[str] = set()
    for ex in _ALL_EXAMPLES:
        rel = str(ex.doc_path.relative_to(DOCS_DIR))
        annotated_docs.add(rel)

    for rel_path in _DOCS_WITH_REQUIRED_ANNOTATIONS:
        assert rel_path in annotated_docs, (
            f"docs/{rel_path} has no annotated examples "
            f"(<!-- test: ... --> annotations required)"
        )


def test_yaml_import() -> None:
    """Sanity: yaml is importable (used by _run_yaml_validate indirectly)."""
    assert yaml is not None


def test_cli_documented_defaults_match_implementation() -> None:
    """docs/reference/cli.md option defaults must match actual CLI defaults.

    Checks two locations: the summary options table and the inline
    'Default: `VALUE`' lines inside each option's detail section.
    """
    cli_ref = DOCS_DIR / "reference" / "cli.md"
    lines = cli_ref.read_text(encoding="utf-8").splitlines()

    def _normalise(v: object) -> str:
        if isinstance(v, bool):
            return str(v).lower()
        return str(v)

    # Build actual defaults from Click introspection
    actual_defaults: dict[str, str] = {}
    for param in main.params:
        if not isinstance(param, click.Option):
            continue
        if param.default is None:
            continue
        long_opt = next((o for o in param.opts if o.startswith("--")), None)
        if long_opt is not None:
            actual_defaults[long_opt] = _normalise(param.default)

    mismatches: list[str] = []

    # --- Pass 1: summary options table ---
    header_idx: int | None = None
    option_col: int = 0
    default_col: int = 0
    for idx, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")][1:-1]
        lowered = [c.lower() for c in cells]
        if "option" in lowered and "default" in lowered:
            header_idx = idx
            option_col = lowered.index("option")
            default_col = lowered.index("default")
            break

    assert header_idx is not None, (
        "docs/reference/cli.md: could not find options table header"
    )

    for line in lines[header_idx + 1 :]:
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.split("|")][1:-1]
        if len(cells) <= max(option_col, default_col):
            continue
        if re.match(r"^[-:]+$", cells[option_col]):
            continue
        option_cell = cells[option_col]
        default_cell = cells[default_col]
        if default_cell in ("—", "-", ""):
            continue
        m = re.search(r"`(--[\w-]+)", option_cell)
        if not m:
            continue
        opt_name = m.group(1)
        table_val = re.sub(r"`", "", default_cell).strip()
        actual = actual_defaults.get(opt_name)
        if actual is not None and table_val != actual:
            mismatches.append(
                f"docs/reference/cli.md (table): {opt_name} documented "
                f"default '{table_val}' but actual CLI default is '{actual}'"
            )

    # --- Pass 2: inline "Default: `VALUE`" in option detail sections ---
    option_heading_re = re.compile(r"^###\s+`(--[\w-]+)")
    inline_default_re = re.compile(r"^Default:\s+`([^`]+)`")
    current_opt: str | None = None
    for line in lines:
        m_heading = option_heading_re.match(line)
        if m_heading:
            current_opt = m_heading.group(1)
        elif line.startswith("## ") or line.startswith("---"):
            current_opt = None
        elif current_opt is not None:
            m_default = inline_default_re.match(line)
            if m_default:
                inline_val = m_default.group(1)
                actual = actual_defaults.get(current_opt)
                if actual is not None and inline_val != actual:
                    mismatches.append(
                        f"docs/reference/cli.md (section {current_opt}): "
                        f"inline 'Default: `{inline_val}`' but actual CLI "
                        f"default is '{actual}'"
                    )

    assert not mismatches, "\n".join(mismatches)
