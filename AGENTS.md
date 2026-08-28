# AGENTS.md

Entry point for an automated agent working in this repository. This file is
deliberately vendor-neutral — an agent needs one place to start regardless of who
made it, and `AGENTS.md` is the convention several tools already read.

It is honest to say where that stops. The longer rule modules live under
`.claude/rules/`, a directory named after one vendor, because that is what loads
them automatically for the author. Their content is not vendor-specific and any
agent can read them; the directory name is a loading convention, not a claim
about who the rules are for.

## What this repository is

A fork of [`KRLabsOrg/verbatim-rag`](https://github.com/KRLabsOrg/verbatim-rag).
Almost all code here was written upstream. `main` is kept byte-identical to
`upstream/main` so contributions can branch cleanly from it; work happens on
branches that are either sent upstream as pull requests or never merged at all.

That has a consequence worth absorbing before changing anything: **most defects
you find belong to someone else's public library.** A breaking change to its API,
a deprecation policy for a compatibility module, or a rename of the project's
identity is the maintainer's decision, not this fork's. Fix what is fixable from
here; record the rest with the reason.

## Read in this order

1. [`README.md`](README.md) — what the product is. The table under
   *What "verbatim" means* is the load-bearing part: it states what the guarantee
   does and does not cover.
2. [`CONTRIBUTING.md`](CONTRIBUTING.md) — repository layout, setup, verification.
3. [`DECISIONS.md`](DECISIONS.md) — why things are the way they are. Read before
   proposing a change that looks obviously missing; it may already be an answered
   question.
4. [`PUBLIC_ROADMAP.md`](PUBLIC_ROADMAP.md) — what upstream intends to do next.
5. [`docs/guide/verbatim-core.md`](docs/guide/verbatim-core.md) — the extraction
   contract, if you are touching spans.

## Surfaces

| Path | What it is | Stability |
|---|---|---|
| `packages/core/verbatim_core/` | Published library: question + context → cited spans | Public API. Additive changes only |
| `verbatim_rag/` | Published library: ingestion, indexing, retrieval, orchestration | Public API. Additive changes only |
| `api/` | FastAPI demo over the above | Prototype, per README |
| `frontend/` | React + Vite demo UI (plain JavaScript, no TypeScript) | Prototype, per README |
| `docker/` | Container dependency lock and its documented overrides | Generated; see `docker/overrides.txt` |

## Verification

`make check` is the gate: lint, format, tests. Run it before calling anything
done, and keep it green at every commit. `make help` lists the rest.

Which check a change needs:

| Changed | Run | Notes |
|---|---|---|
| `packages/core/`, `verbatim_rag/`, `api/`, `tests/` | `make check` | Same paths CI lints |
| `pyproject.toml` dependencies | `make lock`, then `make check` | Regenerates `dev-constraints.txt`; uv keeps existing pins and will not raise versions on its own |
| `docker/`, `Dockerfile`, `docker-compose.yml` | `docker compose up --build`, then `curl -fsS "localhost:${FRONTEND_PORT:-8080}/api/status"` | See `docker/overrides.txt` before regenerating the container lock, and note it needs `--no-emit-package verbatim-core` |
| `frontend/` | `npm ci && npm run build` | Needs Node ≥ 20.19; if the local Node is older, build through `frontend/Dockerfile` (`node:20-alpine`) |
| `docs/`, `mkdocs.yml` | `mkdocs build --strict` | Not installed locally by default; CI runs it |
| `.github/workflows/` | Opening a pull request against `main` | Both workflows filter on `branches: [main]`, so nothing on a branch is checked until a PR exists. The docs *deploy* job runs only on push to `main` and cannot be exercised from a PR — say so rather than claiming it was verified |

Type checking is deliberately absent from `make check`; see `DECISIONS.md`.

## Boundaries

Things that look like cleanup and are not. Do not do these without the
maintainer:

- **Do not weaken span verification.** `_verify_spans` checks every extracted
  span against the text of the document it was attributed to. It is what makes
  the product's claim true, and it is the reason prompt hardening here does not
  sanitise document text: rewriting text the model is asked to quote would make
  correct spans fail verification.
- **Do not change public constructor signatures** in `packages/core/` or
  `verbatim_rag/`. Both are published to PyPI.
- **Do not remove compatibility modules** such as `verbatim_rag/chunking.py`.
  They are deprecated on purpose and their removal schedule is upstream's call.
- **Do not repoint project identity.** `mkdocs.yml` and `CONTRIBUTING.md` name
  `KRLabsOrg/verbatim-rag` because that is the project.
- **Do not add a second mechanism where one exists.** Dependencies are pinned by
  `uv pip compile` into pip-readable constraints; ruff is configured in
  `pyproject.toml`. Adding a parallel config or lock format silently shadows what
  is there. See `.claude/rules/inherited-codebases.md`.

## Secrets

`.env` is git-ignored and read-blocked; `.env.example` is the tracked template
and holds no secret. The LLM key is deliberately not required at startup — the
stack starts without it and reports `llm_configured: false` from `/api/status`.
Never put a real key in a tracked file, a test, or a commit message.

## What is checked in on this branch and why

This branch carries working infrastructure alongside the code changes:
`Makefile`, `dev-constraints.txt`, `.pre-commit-config.yaml`, `.editorconfig`,
`biome.jsonc`, and the rule modules under `.claude/rules/`. That is deliberate,
not spillage.

`Makefile`, the pin set and the hooks are the verification gate this branch was
built behind, and quoting a result without shipping the thing that produced it
is worth less. The rule modules are the working agreement the changes were made
under — including `inherited-codebases.md`, which exists because two changes here
had to be reverted for the same reason and the lesson was worth writing down
rather than remembering.

They are general modules, not a set written for this repository, so parts of them
are inert here and it is more useful to say which than to imply they all applied:
`backend-fastapi.md` covers async SQLAlchemy and Alembic, neither of which this
project uses, and `ai-engineering.md` carries a rule about Cyrillic in prompt
strings that no prompt here contains. What did bind is the rest — the untrusted-
input handling behind `BEY-4`, the injection-over-patching preference visible in
every test double, and `inherited-codebases.md` throughout.

None of it is proposed upstream. This branch is never merged.

## Recording work

Two files, kept distinct:

- [`AUDIT.md`](AUDIT.md) — register of external audit findings. One row each,
  with a status, and for anything closed, **how** and **why that way**.
- [`DECISIONS.md`](DECISIONS.md) — append-only log of non-obvious project
  decisions, newest first. Project decisions only; how your own tooling was set
  up belongs in a commit message.
- [`PRODUCT-MAP.md`](PRODUCT-MAP.md) — the project's own vocabulary, workflows,
  non-goals and success signals on one page, compiled from `README.md` and
  `PUBLIC_ROADMAP.md`. Read it before a product-shaped task; it is a compilation,
  so where it and its sources disagree, the sources win.

Update both in the same commit as the change they describe, not afterwards. If
work stops halfway, the register still has to be true.
