# Working in an inherited codebase

Apply when the repository is a fork, a vendored copy, a legacy project, or any
code whose conventions were set by someone else. Rule levels are defined in
`_LEVELS.md`.

This module exists because of two real incidents in the same session, both the
same shape — a harness default applied without first checking how the repository
already did that job:

- A standalone `ruff.toml` was added to a project that configured ruff in
  `[tool.ruff]`. Ruff reads `ruff.toml` first and ignores `pyproject.toml`
  entirely, so the existing block went inert while still looking authoritative.
- A `uv.lock` was added to a project that already pinned dependencies with
  `uv pip compile` into a pip-readable constraints file consumed by the
  Dockerfile. `uv.lock` cannot be read by pip, so it pinned nothing that the
  build or CI actually installs.

Neither was caught by review or by tests. Both are cheap to prevent and
expensive to notice later, which is why the checks below are mechanical.

## Find the existing mechanism before adding one  [MUST]

Before introducing any config file, lock file, task runner, or tool, find out
how the repository already does that job. The search costs seconds:

- **Config for tool X** — grep `pyproject.toml`, `setup.cfg`, `tox.ini`,
  `package.json` for an `X` section, and look for `X.toml`, `.X.toml`, `.Xrc`,
  `X.config.*`.
- **Dependency pinning** — find every `*.lock`, `constraints*.txt`,
  `requirements*.txt`, then find what *consumes* each one. A pin file nothing
  reads is not a mechanism.
- **Task entry points** — `Makefile`, `justfile`, `scripts/`,
  `[project.scripts]`, `package.json` scripts, and the CI workflow steps.
- **Verification gate** — read the CI workflow before deciding what "green"
  means locally. The gate is whatever CI runs, not whatever the harness prefers.

If a mechanism exists, extend it. Adding a parallel one is the error, not the
choice of tool.

## Never shadow — replace or leave alone  [MUST]

If a file you add makes an existing file inert, that is a replacement, not an
addition. Either do it explicitly — delete the superseded config in the same
change and say why — or do not do it at all.

The test, run after adding the file: does editing the old location still change
behaviour? If it does not, you have shadowed it, and the next reader will edit
the dead file and wonder why nothing happened.

## A pin only counts where it is consumed  [MUST]

Before choosing a lock format, name the thing that will read it. If CI installs
with pip, a lock only pip can read is the one that pins CI; a lock in a format
pip cannot parse pins the author's machine and nothing else.

State the consumer in the change: "`X` is read by `Y`". If no `Y` exists yet,
the change is incomplete — either wire the consumer or say plainly that the
artifact is inert until someone does.

## Measure the blast radius before adopting a preset  [MUST]

Run any new linter, formatter, or type-checker configuration and count what it
reports on code you did not write. Report the number in the change.

Zero findings means the preset is compatible: adopt it. Anything above zero is a
scope decision, not a setup step — mass-rewriting inherited code buries the work
that actually matters in a diff nobody can review. Default to the repository's
existing gate plus whatever additions cost zero.

## New strictness applies to what you touch  [PREFER]

Tighten rules for the files being changed, not for the whole tree. A rule that
would force edits across inherited code needs its own change, its own reasoning,
and usually its own conversation with whoever owns the project.

The exception is a fixer that is provably correct and mechanical — import
ordering, trailing whitespace. Even then, keep it a separate commit and say how
many files it touched.

## Preference is not a technical argument  [MUST]

"I am more used to this tool" does not justify introducing it into a repository
that already solves the problem another way. The cost of a second mechanism is
paid by every future reader, and it is paid in confusion rather than in effort.

When the familiar tool genuinely is better, the change is a migration: replace
the old mechanism, update everything that consumed it, and write down why. If
that is too large for the current task, the answer is to use what is there.

## Record how, not just what  [MUST]

When closing an inherited defect, record the method and why that method, not
only that it is closed. In a codebase whose conventions you did not set, "why
this way" is the part a future reader cannot reconstruct — the alternatives were
usually rejected for reasons visible only at the time.
