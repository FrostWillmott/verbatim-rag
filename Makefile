.PHONY: help install install-hooks lock check fix lint format typecheck test pre-commit ci clean

# The paths CI lints and formats, kept identical to .github/workflows/ci.yml on
# purpose. `ruff check .` also walks examples/ and scripts/, which sit outside
# the CI gate and carry 10 pre-existing findings — linting them here would make
# `make check` disagree with CI.
PY_PATHS := packages/core/verbatim_core/ verbatim_rag/ api/ tests/

# Tools are invoked through the virtualenv directly rather than through
# `uv run`. The pre-commit hooks are `language: system` and must name a real
# path, so they call .venv/bin/ruff; using the same path here is what keeps the
# hook and `make lint` provably the same binary.
VENV := .venv
BIN := $(VENV)/bin

help:
	@echo "Project Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install       - Install into .venv, pinned by dev-constraints.txt"
	@echo "  make install-hooks - Install pre-commit hooks into .git/hooks"
	@echo "  make lock          - Regenerate dev-constraints.txt from pyproject.toml"
	@echo ""
	@echo "Code Quality:"
	@echo "  make check         - Run the CI gate locally (lint + format + tests)"
	@echo "  make fix           - Auto-fix lint and format issues"
	@echo "  make lint          - Run linter (ruff check)"
	@echo "  make format        - Check formatting (ruff format --check)"
	@echo "  make typecheck     - Deferred in this branch, see DECISIONS.md"
	@echo "  make test          - Run tests"
	@echo "  make pre-commit    - Run hooks against staged files"
	@echo "  make ci            - Alias for check"

$(BIN)/python:
	uv venv $(VENV)

# Installs against the pinned set in dev-constraints.txt. Package names come from
# the dev extra of pyproject.toml and versions from the constraints file, so
# neither is restated here. Core is installed first and editable, the same order
# CI and the Dockerfile use, so the local package wins over the PyPI release.
install: $(BIN)/python
	uv pip install --python $(BIN)/python -c dev-constraints.txt -e packages/core/
	uv pip install --python $(BIN)/python -c dev-constraints.txt -e ".[dev]"

# Regenerates the pinned set. Mirrors how docker/constraints.txt is produced —
# see docker/overrides.txt for the container equivalent and its caveats.
# --universal resolves with environment markers rather than for this host, so one
# file covers the whole 3.10/3.11/3.12 CI matrix and both arm64 and x86_64.
# verbatim-core is excluded because it resolves to an editable local path, and
# pip rejects editable entries inside a constraints file.
# uv preserves existing pins: this will not raise versions on its own.
lock:
	uv pip compile pyproject.toml --extra dev --universal \
	    --no-emit-package verbatim-core -o dev-constraints.txt

install-hooks:
	$(BIN)/pre-commit install

check: lint format test

fix:
	$(BIN)/ruff check --fix $(PY_PATHS)
	$(BIN)/ruff format $(PY_PATHS)

lint:
	$(BIN)/ruff check $(PY_PATHS)

format:
	$(BIN)/ruff format --check $(PY_PATHS)

# TODO: wire mypy. Deliberately not part of `check` — mypy is declared nowhere in
# this repository, there is no [tool.mypy] section, and the inherited code has
# never been type-checked. A `check` target that can never go green is worse than
# an honest gap. See the DECISIONS.md entry of 2026-08-27 for the full reasoning
# and what adopting it would take.
typecheck:
	@echo "SKIPPED: mypy is not wired in this branch. See DECISIONS.md (2026-08-27)."

test:
	$(BIN)/pytest tests/ -v

# Deliberately not --all-files: trailing-whitespace and end-of-file-fixer would
# rewrite 68 inherited files that are outside this branch's scope. Bare
# `pre-commit run` covers the staged set, which is what the hook enforces anyway.
pre-commit:
	$(BIN)/pre-commit run

ci: check

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
