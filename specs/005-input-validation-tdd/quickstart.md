# Quickstart: Input Validation Tests

**Branch**: `005-input-validation-tdd`
**Phase**: 1 — Design

---

## Running the new tests

All new tests are in the default (non-slow) test run:

```bash
# Run all tests including the new ones
cd src && uv run pytest

# Run only the contract tests (CLI boundary cases)
cd src && uv run pytest tests/contract/

# Run only the unit tests (loader-level boundary cases)
cd src && uv run pytest tests/unit/
```

---

## TDD workflow for this feature

For each missing case, the sequence is:

```bash
# 1. Write the failing test (or the documenting test if behaviour exists)
#    Edit tests/unit/test_validator.py, tests/unit/test_history.py,
#    or tests/contract/test_cli_contract.py

# 2. Run only the new test to confirm its status
cd src && uv run pytest tests/unit/test_history.py::TestLoadHistory::test_load_history_directory_raises -v

# 3. If RED: add the minimal production-code fix (is_dir guard / empty guard)
#    Then re-run until GREEN

# 4. Run the full suite to check for regressions
cd src && uv run pytest --cov=src/buddy_scheduler --cov-report=term-missing
```

---

## Verifying the new error messages manually

```bash
# Team path is a directory
buddy-scheduler --team /tmp

# History path is a directory (existing team file required)
buddy-scheduler --team examples/team.yaml --history /tmp/some-dir/

# History file contains non-JSON content
echo "not json" > /tmp/bad-history.json
buddy-scheduler --team examples/team.yaml --history /tmp/bad-history.json

# History file has correct JSON but wrong schema (array instead of object)
echo '[1,2,3]' > /tmp/schema-wrong.json
buddy-scheduler --team examples/team.yaml --history /tmp/schema-wrong.json

# Zero weight values (both should succeed)
buddy-scheduler --team examples/team.yaml --history-weight 0.0
buddy-scheduler --team examples/team.yaml --tz-weight 0.0

# Non-numeric weight (should exit non-zero with a usage error)
buddy-scheduler --team examples/team.yaml --history-weight high
```

---

## Expected outputs

**Directory as team path**:
```json
{
  "success": false,
  "error": "Team roster path is a directory, not a file: /tmp"
}
```
Exit code: `1`

**Zero history weight** — no error, normal pairing output:
```json
{
  "success": true,
  "pairs": [["Alice", "Bob"]],
  ...
}
```
Exit code: `0`

**Non-numeric weight** — Click usage error on stderr, no JSON on stdout:
```
Error: Invalid value for '--history-weight': 'high' is not a valid float.
```
Exit code: `2`
