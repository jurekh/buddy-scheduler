# Data Model: Input Validation — Invalid Paths and Malformed Files

**Branch**: `005-input-validation-tdd`
**Phase**: 1 — Design

This feature adds no new persistent data, public models, or runtime entities.
The "data model" here describes the validation rules being added to two existing
loader functions, expressed as pre-conditions and failure modes.

---

## `load_team_roster(path: Path)` — extended validation rules

| Guard | Condition | Exception raised | Message pattern |
|-------|-----------|-----------------|-----------------|
| Access check | `path.exists()` raises `OSError` | `FileLoadError` | `"Cannot access team roster file {path}: {exc}"` |
| Not found | `not path.exists()` | `FileLoadError` | `"Team roster file not found: {path}"` |
| **Is directory** | `path.is_dir()` | `FileLoadError` | `"Team roster path is a directory, not a file: {path}"` *(new)* |
| Read error | `path.read_text()` raises `OSError` | `FileLoadError` | `"Cannot read team roster file {path}: {exc}"` |
| YAML error | `yaml.safe_load()` raises `YAMLError` | `FileLoadError` | `"Team roster file is not valid YAML: {exc}"` |
| Empty content | `not data` (None from YAML) | `FileLoadError` | `"Team roster file is empty: {path}"` |
| Not a list | root is not `list` | `FileLoadError` | `"Team roster file must contain a YAML list…"` |

The **Is directory** row is the new guard added by this feature. All other rows
document pre-existing behaviour.

---

## `load_history(path: Path)` — extended validation rules

| Guard | Condition | Exception raised | Message pattern |
|-------|-----------|-----------------|-----------------|
| Access check | `path.exists()` raises `OSError` | `FileLoadError` | `"Cannot access history file {path}: {exc}"` |
| Not found | `not path.exists()` | `FileLoadError` | `"History file not found: {path}"` |
| **Is directory** | `path.is_dir()` | `FileLoadError` | `"History path is a directory, not a file: {path}"` *(new)* |
| Read error | `path.read_text()` raises `OSError` | `FileLoadError` | `"Cannot read history file {path}: {exc}"` |
| **Empty content** | `not raw.strip()` | `FileLoadError` | `"History file is empty: {path}"` *(new)* |
| JSON parse error | `json.loads()` raises `JSONDecodeError` | `FileLoadError` | `"History file is not valid JSON: {exc}"` |
| Schema error | `_HistoryModel.model_validate()` fails | `DataValidationError` | `"History validation failed: {exc}"` |

The **Is directory** and **Empty content** rows are new. All other rows document
pre-existing behaviour.

---

## CLI weight parameter validation rules

| Parameter | Validation | Where | Message pattern |
|-----------|-----------|-------|-----------------|
| `--history-weight` | Value must be `>= 0.0` | `_run()` in `cli.py` | `"--history-weight must be >= 0.0, got {v}"` |
| `--tz-weight` | Value must be `>= 0.0` | `_run()` in `cli.py` | `"--tz-weight must be >= 0.0, got {v}"` |
| Both | Value `0.0` is **valid** | (boundary of above) | n/a — passes through |
| Both | Non-numeric string | Click `type=float` at parse time | Click usage error (exit 2) |

No changes to these rules. The table documents them for test authoring clarity.
