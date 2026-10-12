# buddy-scheduler

Command-line tool that pairs team members for buddy check-ins. Pairings are
computed with a Mixed Integer Programming solver (PuLP/CBC) that takes into
account timezone compatibility, how often two people have been paired before,
and explicit avoidance constraints.

## Quick start

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv run buddy-scheduler --team examples/team.yaml
uv run buddy-scheduler --team examples/team.yaml --history team.history.json --update-history
```

Output is JSON on stdout; logs go to stderr.

## Documentation

- Tutorial: [Getting started](docs/tutorial/getting-started.md)
- How-to: [Avoid pairings](docs/how-to/avoid-pairings.md),
  [Manage absences](docs/how-to/manage-absences.md),
  [Track history](docs/how-to/track-history.md)
- Reference: [CLI](docs/reference/cli.md),
  [Team YAML](docs/reference/team-yaml.md),
  [Output format](docs/reference/output-format.md)
- Explanation: [How the MIP model works](docs/explanation/how-mip-works.md)

## Development

| Command | Purpose |
|---|---|
| `make install` | Install runtime and dev dependencies |
| `make test` | Run tests (excluding slow) with coverage gate |
| `make test-full` | Run all tests, including slow fuzz/performance tests |
| `make lint` | ruff lint and format check |
| `make format` | Apply ruff formatting |
| `make typecheck` | mypy strict |
| `make build` | Build sdist and wheel |
| `make snap` | Build the snap package |
| `make clean` | Remove build artifacts and caches |

## License

MIT. See [LICENSE](LICENSE).
