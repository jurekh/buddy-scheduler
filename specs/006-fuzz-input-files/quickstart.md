# Quickstart: Running the Fuzz Test Suite

**Branch**: `006-fuzz-input-files`
**Created**: 2026-03-03

---

## Prerequisites

Ensure the dev dependencies are installed (includes `hypothesis`):

```bash
uv sync
```

---

## Run the fuzz tests

Fuzz tests are tagged `@pytest.mark.slow` and excluded from the default `pytest` run.
To run them explicitly:

```bash
# From repo root
uv run pytest -m slow -v
```

Expected output: the three fuzz test classes
(`TestFuzzTeamRoster`, `TestFuzzHistory`, `TestFuzzCLI`) each run 100 generated
examples per test method.

---

## Run with a fixed seed (deterministic)

To reproduce a specific run or verify CI results locally:

```bash
uv run pytest -m slow --hypothesis-seed=42 -v
```

Any seed value works. If hypothesis found a failure and printed `Falsifying example ...`
along with a seed, pass that seed to reproduce the exact failure:

```bash
uv run pytest -m slow --hypothesis-seed=<seed from failure output> -v
```

---

## Run only the YAML safe-load enforcement test

This test is NOT marked `@pytest.mark.slow` and runs in the default suite:

```bash
uv run pytest tests/fuzz/test_fuzz_loaders.py::TestYamlSafeLoadEnforcement -v
```

---

## Run the full default suite (excludes fuzz tests)

```bash
uv run pytest
```

This confirms no regressions in existing tests after adding the `hypothesis` dependency
and the new `tests/fuzz/` module.

---

## Run everything (default + fuzz)

```bash
uv run pytest -m '' -v
# or equivalently:
uv run pytest --override-ini="addopts=" -v
```

---

## Coverage with fuzz tests included

```bash
uv run pytest -m '' --cov=buddy_scheduler --cov-report=term-missing
```

---

## Scenarios exercised

### Scenario 1: Random bytes fed to team roster loader

```bash
uv run pytest tests/fuzz/test_fuzz_loaders.py::TestFuzzTeamRoster::test_binary_content_never_crashes -m slow -v
```

hypothesis generates random byte sequences (including non-UTF-8) and verifies each call
to `load_team_roster` terminates with `FileLoadError` or `DataValidationError`.

### Scenario 2: Valid-looking YAML with generated member fields

```bash
uv run pytest tests/fuzz/test_fuzz_loaders.py::TestFuzzTeamRoster::test_structured_yaml_never_crashes -m slow -v
```

hypothesis generates YAML-serialized lists of dicts with generated `name`, `timezone`,
`active`, and `avoid_buddies` values that straddle boundary conditions.

### Scenario 3: Arbitrary bytes to history loader

```bash
uv run pytest tests/fuzz/test_fuzz_loaders.py::TestFuzzHistory::test_binary_content_never_crashes -m slow -v
```

### Scenario 4: Deeply nested JSON structures

```bash
uv run pytest tests/fuzz/test_fuzz_loaders.py::TestFuzzHistory::test_nested_json_never_crashes -m slow -v
```

hypothesis uses `st.recursive()` to generate deeply nested JSON (up to 500 leaf nodes)
and verifies no stack overflow or memory exhaustion occurs.

### Scenario 5: CLI exit code contract

```bash
uv run pytest tests/fuzz/test_fuzz_loaders.py::TestFuzzCLI -m slow -v
```

hypothesis generates arbitrary content for the `--team` and `--history` CLI arguments
and verifies the process always exits with code 0 or 1.

---

## Interpreting a hypothesis failure

When hypothesis finds a failing input it outputs:

```
Falsifying example: test_binary_content_never_crashes(
    content=b'\x80...',
)

Unexpected exception ValueError: ...
```

To reproduce:

```bash
uv run pytest tests/fuzz/test_fuzz_loaders.py::TestFuzzTeamRoster::test_binary_content_never_crashes \
  --hypothesis-seed=<seed> -m slow -v -s
```

Then investigate the unexpected exception in the loader and add a corresponding guard.
