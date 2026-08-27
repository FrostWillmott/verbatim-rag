# Contributing to Verbatim RAG

Thanks for your interest in contributing. Verbatim has a lightweight extraction
package and a broader reference RAG stack, so first identify which surface your
change affects.

## Repository structure

```text
packages/core/verbatim_core/   # verbatim-core: question + context -> cited excerpts
verbatim_rag/                  # verbatim-rag: retrieval, indexing, and orchestration
api/                           # FastAPI development surface
frontend/                      # Vite/React development UI
tests/                         # network-free verbatim-core tests
docs/                          # MkDocs documentation
```

Research training and canonical paper evaluation live in
[`KRLabsOrg/acl-verbatim`](https://github.com/KRLabsOrg/acl-verbatim), not in
the supported runtime API of this repository.

## Setup

Create a Python 3.10+ virtual environment, then install the surface you need.

```bash
git clone https://github.com/KRLabsOrg/verbatim-rag.git
cd verbatim-rag
make install
```

`make install` creates `.venv` and installs the core package, the root package
and the dev tooling against `dev-constraints.txt`, the generated pin set. Tool
versions are declared once, in the `dev` extra of `pyproject.toml`; regenerate
the pin set with `make lock` after changing a dependency.

To work on the extraction core alone, without the ML and vector-store stack:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -c dev-constraints.txt -e packages/core/
pip install -c dev-constraints.txt pytest pytest-asyncio
```

The `-c` matters: it is what keeps a local install on the same versions as CI.

The core runtime depends on `openai`, `pydantic`, `rapidfuzz`, and `jinja2`.
The optional model extra and full RAG package add substantially heavier ML,
document-processing, and vector-store dependencies.

## Verification

Run the checks that match the files you changed and list the exact commands in
your pull request.

```bash
make check      # lint, format and the full test suite with the coverage floor
make test-core  # only what an environment without the root package can run
```

`make help` lists the rest. The commands live in the `Makefile` rather than here
so that this file and CI cannot drift apart; `make check` runs what CI runs.

For packaging changes:

```bash
python -m build packages/core
python -m build .
```

For frontend changes:

```bash
cd frontend
npm ci
npm run build
```

CI gates the network-free `verbatim-core` tests on Python 3.10–3.12, Ruff across
the core, full-RAG and API sources, the RAG and API test suites with a coverage
floor, the frontend lint and build on Node 20, both container image builds,
dependency auditing, and distribution builds.

Two things it still does not cover, so include focused evidence in the pull
request when you touch them: model downloads, which no job performs, and the
frontend beyond a successful build — there is no UI test framework yet.

## Issues and discussions

Use [Discussions](https://github.com/KRLabsOrg/verbatim-rag/discussions) for
questions, early designs, research directions, and uncertain product ideas. Use
an issue for a reproducible bug or a bounded implementation with testable
acceptance criteria.

Labels clarify readiness:

- `good first issue` is a small, independently testable change with code
  pointers, non-goals, and a start command;
- `help wanted` is ready for outside implementation or investigation but may
  require more context than a first issue;
- `design` needs an interface or behavior decision before implementation;
- `research` is exploratory and may end in a negative result or design note;
- `correctness` affects extraction, provenance, evaluation, or another stated
  contract;
- `status: claimed` means someone is actively working on it—coordinate before
  starting a competing implementation.

Comment on an unclaimed contributor issue before doing substantial work.
Maintainers will assign it or add `status: claimed`. If the issue changes after
investigation, post the evidence before expanding the PR.

## Pull requests

1. Branch from `main` and keep the PR focused on one issue or decision.
2. Add tests for behavior and regression fixes.
3. Explain any change to span validation, citations, templates, schemas,
   defaults, or compatibility.
4. Update public documentation and `CHANGELOG.md` for user-facing behavior.
5. Remove credentials and private document text from tests, logs, and fixtures.
6. Complete the contribution-rights checkbox in the PR template. CI enforces it.

## Contribution rights

By submitting a pull request you confirm that you wrote the contribution (or
have the right to submit it) and that it may be distributed under this
repository's MIT license. This is what the required checkbox in the PR template
attests. You may also sign off commits with `git commit -s`
([DCO](https://developercertificate.org/)); appreciated, not required.

## Releasing

`verbatim-core` and `verbatim-rag` currently share a version number.

1. Update `packages/core/pyproject.toml`, `pyproject.toml`, and
   `verbatim_rag/__init__.py` together.
2. Update `CHANGELOG.md`.
3. Build both distributions and inspect them.
4. Tag the release and publish `verbatim-core` before `verbatim-rag`.

```bash
python -m build packages/core
python -m build .
twine check packages/core/dist/* dist/*
```

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
