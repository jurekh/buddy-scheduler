.PHONY: all install test lint format typecheck build clean

all: install test lint typecheck

install:
	uv sync --all-groups

test:
	uv run pytest tests --cov=src/buddy_scheduler --cov-report=term-missing

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests

typecheck:
	uv run mypy src

build:
	uv build

clean:
	rm -rf .venv .mypy_cache .ruff_cache dist .pytest_cache htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
