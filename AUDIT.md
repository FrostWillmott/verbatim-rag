# Audit remediation

Register of the ten audit reports dated 2026-08-26, all taken against commit
`88f510a`. One row per finding: what it is, what was done, and why. Kept current
as work lands.

A `done` row states **how** the finding was closed and **why that way**, not just
that it is closed. The method is the part a future reader cannot reconstruct: in
a codebase whose conventions someone else set, the rejected alternatives were
usually rejected for reasons visible only at the time. A row that says only
"fixed" has thrown that away.

This file tracks what happens to each finding. `DECISIONS.md` carries the longer
reasoning behind the non-obvious calls; rows here link to it rather than repeat it.

## Premise

The reports were produced against `anastasiakrivova-stack/verbatim-rag`, a fork
of this repository, which is itself a fork of `KRLabsOrg/verbatim-rag`. At the
audited commit `88f510a` all three trees are identical: the reports' own platform
data shows the audited copy at `ahead_by=0, behind_by=0` against its parent, and
this repository's `main` is likewise `0/0` against `upstream/main`.

The findings therefore describe upstream code. This fork existed as a base for
pull requests rather than as a project of its own; the work it carries was
merged upstream.

That is what makes some findings unactionable from here rather than merely
inconvenient — breaking changes to a public API, a deprecation policy for a
compatibility layer, or the open-source report's suggestion to "add a delta of
your own", which in practice means presenting someone else's library as your own
project. Those rows are marked `rejected` with the reason rather than skipped.

The branch is based on `88f510a` so every finding is reproducible from its
starting point, and it is never merged: `main` stays a byte-identical mirror of
upstream.

## Legend

| Status | Meaning |
|---|---|
| `done` | Fixed on this branch |
| `todo` | Accepted, not started |
| `rejected` | Deliberately not doing — reason in the row |
| `deferred` | Real, but out of reach in the time or ownership available — reason in the row |
| `upstream` | Already fixed before the audit landed, in an upstream pull request |
| `n/a` | Not applicable |

Severity is the audit's own rating, kept verbatim so the register can be read
against the reports.

## Scoreboard

| Audit | Score | Findings | done | todo | rejected / deferred | n/a |
|---|---:|---:|---:|---:|---:|---:|
| Dependency hygiene | 18/100 | 10 | 2 | 6 | 2 | 0 |
| Security | 25/100 | 5 | 3 | 1 | 1 | 0 |
| CI/CD | 32/100 | 6 | 1 | 3 | 2 | 0 |
| Configuration hygiene | 40/100 | 4 | 2 | 2 | 0 | 0 |
| Test quality | 42/100 | 5 | 0 | 4 | 1 | 0 |
| Dead code | 57/100 | 7 | 1 | 5 | 1 | 0 |
| Cognitive debt | 59/100 | 5 | 2 | 2 | 1 | 0 |
| AI readiness | 60/100 | 5 | 3 | 1 | 1 | 0 |
| Codebase hygiene | 71/100 | 5 | 0 | 3 | 2 | 0 |
| Open-source readiness | 100/100 | 0 | — | — | — | — |

The 100/100 on open-source readiness is not a result. The report applies a
domain no-op for a pure fork with no delta of its own and skips all 14 criteria;
the score means "nothing applicable to assess", not "excellent". It also stops
being true the moment this branch exists.

## Security — 25/100

| ID | Finding | Sev | Status | Note |
|---|---|---|---|---|
| SEC-1 | `docs.yml` installs unpinned public packages in a job with `contents: write` | critical | `done` | **How:** every `pip install` in both workflows now runs against `dev-constraints.txt`, the same generated pin set `make install` uses; the tools were added to the `dev` extra so one file covers local, CI and docs. **Why this way:** it is the mechanism this repository already uses — `docker/constraints.txt` is produced by the same `uv pip compile` and consumed by the Dockerfile as `pip install -c`. **Evidence:** the deploy job itself only runs on push to `main`, so it could not be exercised from a pull request; instead its exact install command was run locally against a clean venv with pip, and resolved to the pinned `mkdocs-material 9.7.7`, `mkdocstrings 1.0.6`, `mkdocs 1.6.1`. **What this does not do:** version pinning stops a freshly published release from being pulled; it is not hash verification. `--generate-hashes` with `--require-hashes` is the next increment. |
| SEC-2 | `trust_remote_code=True` with no pinned `revision` — 7 call sites | high | `done` | **How:** every loader now takes an optional `revision`, forwards it, and calls `warn_if_remote_code_is_unpinned` — a guard in `verbatim_core/remote_code.py` that logs once per model when remote code will run from a mutable default branch. Six real call sites across `extractors.py`, `rerankers.py` and `extractor_models/train.py`; the seventh was a docstring. **Why this way:** pinning a commit SHA for the default models was the tempting move and would have been guesswork — they are `KRLabsOrg`, `zilliz` and `jinaai` repositories, not ours, and a wrong pin breaks loading for everyone. The parameter is additive, so nothing existing changes behaviour, and the operator gets both the lever and a reason to use it. What was silent is now visible; what to pin stays the maintainer's call (see the maintainer questions in the plan). |
| SEC-3 | Raw Milvus filter expressions passed through unvalidated | medium | `rejected` | Replacing `filter: str` with a typed allowlist schema is a redesign of the library's public query API. Not a call to make unilaterally in a fork of someone else's project. |
| SEC-4 | No bound on `num_docs` / context size; shared `rag.k` mutated per request | medium | `done` | **How:** `num_docs` and `k` are bounded to 1–50 and the transform context to 100 items of 100 000 characters. Measured: a request with 10 000 context items kept the endpoint busy **41 seconds** before the caps and is refused in **0.03 s** after. **Why this way:** literal caps rather than new settings — we had just finished removing options that were declared and did nothing, and an unwired `MAX_NUM_DOCS` would have recreated that problem. |
| SEC-5 | Production frontend build publishes source maps | low | `todo` | One line in `frontend/vite.config.js`. |

None of the ten reports examines the prompt-injection surface, although the
product feeds retrieved document text into an LLM prompt. It is recorded as BEY-4
under "Beyond the audit", with the scope narrower than first written: span
verification already blocks fabrication and misattribution, so the exposure is
suppression, not invention.

## Dependency hygiene — 18/100

| ID | Finding | Sev | Status | Note |
|---|---|---|---|---|
| DEP-1 | `axios 1.13.2` — vulnerability cluster in a direct frontend dependency | high | `todo` | Already filed upstream as issue #48; fixable without `--force`. |
| DEP-2 | `transformers 4.53.3` — model-loading / code-execution advisories | high | `deferred` | The only high-severity finding deliberately postponed. A 4.x → 5.x major upgrade of the ML stack cannot be verified in the available time without running model downloads; a blind bump that breaks model loading is worse than the open advisory. Last item in the plan — done only if time remains, and only with a real run. |
| DEP-3 | CI tools installed unpinned; docs deploy holds write permission | high | `done` | **How:** `ruff`, `pytest`, `pytest-asyncio`, `build`, `twine` and `pip-audit` are declared in the `dev` extra and installed with `-c dev-constraints.txt`. Verified locally with pip: `ruff` resolved to the pinned 0.16.4, `build` to 1.5.0. **Why this way:** declaring them in the manifest keeps one source for the version and lets `make lock` carry them, rather than a second list maintained inside the workflow. The write permission on the deploy job stays — `mkdocs gh-deploy` needs it; what changed is that it no longer runs unpinned third-party install code. |
| DEP-4 | `datasets 3.4.1` — CVE-2026-66007 | medium | `todo` | Regenerating `docker/constraints.txt` needs an explicit upgrade flag: `uv pip compile` preserves existing pins and will not raise them on its own. |
| DEP-5 | `aiohttp 3.14.2` — transitive, out-of-bounds read | medium | `todo` | Same regeneration caveat as DEP-4. |
| DEP-6 | `python-multipart 0.0.22` in a stale `api/requirements.txt` | medium | `todo` | Confirmed: the file is referenced by nothing — not the Dockerfile, not CI. Deleting it is likely the right fix, not bumping it. |
| DEP-7 | Docker base images pinned by floating tag, not digest | medium | `todo` | `python:3.11-slim`, `node:20-alpine`, `nginx:alpine`. |
| DEP-8 | Frontend build-tool vulnerabilities (vite, postcss, rollup, …) | medium | `todo` | Build-time and dev only; not present in the nginx runtime image. |
| DEP-9 | `setuptools<81` held by a documented exception with no review date | low | `rejected` | The exception is correct and well documented in `docker/overrides.txt`: milvus-lite 2.x imports `pkg_resources`, removed in setuptools 81. Adding a review date to someone else's constraint file without owning the upgrade path is paperwork, not a fix. |
| DEP-10 | No root Python lockfile (improvement step 3) | — | `done` | **How:** `dev-constraints.txt`, generated by `make lock` (`uv pip compile pyproject.toml --extra dev --universal`), consumed by `make install` as `pip install -c`. **Why this way:** the repository already locks exactly like this — `docker/overrides.txt` documents the same command producing `docker/constraints.txt`, which the Dockerfile consumes with `pip install -c`. A first attempt used `uv.lock` + `uv sync` and was reverted: pip cannot read `uv.lock`, and CI installs with pip, so it would have pinned nothing that is actually built. `uv sync` also takes ownership of `.venv` and prunes it. See DECISIONS.md. |

## CI/CD — 32/100

| ID | Finding | Sev | Status | Note |
|---|---|---|---|---|
| CI-1 | Checks are not required to merge into `main` | high | `rejected` | Branch protection on a fork where the same person opens and merges every pull request is ceremony, not a gate. The finding is correct for the upstream repository. |
| CI-2 | No registered workflows or runs — Actions appear disabled on the fork | high | `todo` | Actions are off by default on forks. Must be enabled before anything on this branch is ever checked. |
| CI-3 | Frontend build is not part of CI | medium | `todo` | |
| CI-4 | Container images are never built in CI | medium | `todo` | |
| CI-5 | Package release is fully manual | medium | `rejected` | Release automation for a fork that publishes nothing has no meaning. Belongs upstream. |
| CI-6 | Runner image, action refs and pip installs allow version drift | low | `done` | **How:** pip installs pinned via constraints (DEP-3); `actions/checkout` and `actions/setup-python` pinned to commit SHAs with the tag kept as a trailing comment. **Why this way:** a tag is mutable and an action runs as code inside the workflow, so it belongs in the same class as a package. `ubuntu-latest` is deliberately left floating: it is GitHub-maintained, pinning it buys maintenance work rather than supply-chain safety. |

## Configuration hygiene — 40/100

| ID | Finding | Sev | Status | Note |
|---|---|---|---|---|
| CFG-1 | Declared API settings do not affect the container run path | high | `done` | Confirmed, and worse than reported — the `API_*` names were inert entirely (BEY-6). **How:** `MAX_QUESTION_LENGTH` now reaches `APIService` through `get_api_service` instead of a hardcoded `1000`; `TEMPLATES_PATH` is loaded into the template manager that actually renders answers; `LOG_LEVEL` is applied in `create_app` with `force=True`, since the old module-level `basicConfig` ran before the config was read and a second call would otherwise be a no-op. **Why this way:** each setting got the answer its own evidence supported rather than one blanket treatment — see DEAD-2 for the third, which was removed instead of wired. `API_HOST`/`API_PORT` remain direct-run-only by design: the container's entrypoint supplies host and port to uvicorn, and making the Dockerfile read them would move deployment configuration into the image for no gain. |
| CFG-2 | `.env.example`, README, Compose and code defaults disagree | medium | `todo` | `INDEX_PATH` (`./index.db` vs `/data/index.db`) and `FRONTEND_PORT` (8080 vs 80). The port half is already fixed upstream in PR #46 — will be fixed here as well *and* cross-referenced, so the register does not read as if the work were new. |
| CFG-3 | Configuration errors surface late or silently | medium | `done` | The check was worse than reported: `"OPENAI_API_KEY" not in os.environ` tests presence, not content, while `.env.example` ships the variable **empty** — so the likeliest broken setup produced no warning at all. **How:** `llm_key_is_configured()` treats blank as missing, the warning goes through the logger during app creation instead of `print` at import, and `/api/status` now carries `llm_configured` so the state is visible before the first query rather than after it. `apply_template_config` logs which branch it took. **Why this way:** not a hard failure — `.env.example` documents on purpose that a missing key does not stop the stack, so the defect was the silence, not the tolerance. |
| CFG-4 | Runtime decisions hidden as code constants | low | `todo` | Model, endpoint, embedding and collection name in `api/dependencies.py`. Decide per value: promoted to a documented setting, or marked as a deliberate demo constant. |

## Test quality — 42/100

| ID | Finding | Sev | Status | Note |
|---|---|---|---|---|
| TST-1 | The RAG happy path (`verbatim_rag`) has no tests at all | — | `todo` | Largest single gap. Needs fake vector-store and embedding providers so it runs without external services. |
| TST-2 | No contract tests for the FastAPI surface | — | `todo` | Highest value per hour: it is where the confirmed live bugs are, so the tests double as proof of the fixes. |
| TST-3 | No coverage target; coverage measured ad hoc for core only | — | `todo` | Core measures 48%; project-wide is estimated at ~14%. |
| TST-4 | No frontend test framework at all | — | `deferred` | Standing up Vitest or Playwright is a day of work by itself, and the frontend components most in need of testing are the ones scheduled for deletion under DEAD-1. Revisit only if the schedule holds. |
| TST-5 | No fake-provider harness; test layers not separated | — | `todo` | Prerequisite for TST-1; lands with it. |

## Dead code — 57/100

| ID | Finding | Sev | Status | Note |
|---|---|---|---|---|
| DEAD-1 | Nine unreachable frontend components importing modules that no longer exist | HIGH | `todo` | Already filed upstream as issue #47. |
| DEAD-2 | `template_id`, `MAX_QUESTION_LENGTH`, `TEMPLATES_PATH` declared but detached | HIGH | `done` | **How:** `template_id` removed from the request schema and from the service signatures; `QueryRequestModel` now sets `extra="forbid"`, so sending it returns 422 instead of a 200 with an unchanged answer. The other two were wired — see CFG-1. **Why this way:** the other two had a consumer to connect to, `template_id` had none: neither `VerbatimRAG.query` nor `query_async` takes such a parameter, so honouring it would mean changing the public API of the upstream library. Removing a parameter that never worked is the honest half of the same finding. |
| DEAD-3 | Direct frontend dependencies with no live imports | MEDIUM | `todo` | `react-icons`, `cmdk`, several Radix primitives. Follows DEAD-1. |
| DEAD-4 | API service layer partly bypassed; async signature out of sync | MEDIUM | `todo` | Understated in the report — this is a live defect, not untidiness. See BEY-1. |
| DEAD-5 | Legacy template helpers in core no longer called | LOW | `todo` | `_generate_template`, `_fill_template_enhanced`, `MARKING_SYSTEM_PROMPT`. |
| DEAD-6 | Zero-byte and copy-like public assets | LOW | `todo` | Four 0-byte PNGs plus ` copy` duplicates; overlaps HYG-3. |
| DEAD-7 | Deprecation policy for `chunking` and the reserved `answer` parameter | INFO | `rejected` | Setting a removal version for a public compatibility layer is the upstream maintainer's call, not a fork's. |

## Cognitive debt — 59/100

| ID | Finding | Sev | Status | Note |
|---|---|---|---|---|
| CD-1 | No local entry point carrying product intent and safe-change boundaries | medium | `done` | **How:** the *Boundaries* section of `AGENTS.md` names what looks like cleanup and is not — weakening span verification, changing published constructor signatures, removing compatibility modules, repointing project identity, adding a parallel config mechanism. Each with its reason. **Why this way:** a list of prohibitions without reasons gets argued with; the reason is what makes it hold. |
| CD-2 | Executable specs strong for core, weak for full RAG / API / frontend | medium | `todo` | Same work as TST-1 and TST-2. |
| CD-3 | Fork decisions not reconstructable without upstream history | medium | `done` | **How:** the Premise section above names the authoritative source, this fork's role, and where divergence is recorded — rows in this file and entries in `DECISIONS.md`. **Why this way:** a note inside the repository rather than a link out, because the finding is precisely that a reader holding only the fork cannot tell inherited code from ours. Kept to verifiable facts — the audited commit, the fork chain, the platform counters — so it reads as context rather than as a defence of the work. |
| CD-4 | Repository identity points at upstream more strongly than at the fork | medium | `rejected` | `mkdocs.yml` and `CONTRIBUTING.md` correctly identify `KRLabsOrg/verbatim-rag`: that *is* the project. Rewriting them to point at the fork would misrepresent authorship. The honest fix is CD-3 — say plainly that this is a fork and what diverges. |
| CD-5 | Historical design context (`docs/verbatim_blog.md`) outside the docs nav | low | `todo` | |

## AI readiness — 60/100

| ID | Finding | Sev | Status | Note |
|---|---|---|---|---|
| AIR-1 | No `AGENTS.md` or equivalent cross-agent entry point | high | `done` | **How:** `AGENTS.md` at the root — 99 lines covering what the repository is, a reading order, the surfaces and their stability, the verification matrix, the boundaries, and where decisions are recorded. **Why this way:** vendor-neutral, naming no assistant. Answering "there is no cross-agent entry point" with a directory named after one vendor would have missed the finding. Every link in it was checked to resolve. |
| AIR-2 | No one-command verification matrix per surface | high | `done` | **How:** `make check` runs the CI gate locally, and `AGENTS.md` carries the per-surface table: changed path → command → caveat. **Why this way:** the caveats are the useful part, so they are in the table rather than omitted — the frontend needs Node ≥ 20.19, mkdocs is not installed locally, and the docs deploy job cannot be exercised from a pull request at all. A matrix that implies everything is checkable would be worse than none. |
| AIR-3 | `/api/load-resources` and the env contract are out of sync | medium | `todo` | Confirmed: `frontend/src/contexts/ApiContext.js:218` posts to a route that `api/app.py` does not define. Overlaps DEAD-2. |
| AIR-4 | No durable planning memory or handoff format | medium | `done` | **How:** two files with separate jobs — this register for what happens to each finding, `DECISIONS.md` for why non-obvious choices were made — plus the rule in `AGENTS.md` that both are updated in the same commit as the change. **Why this way:** the failure mode is a register that lies after work stops halfway, so the convention is written down rather than left to habit. Not a full ADR process; that would be over-engineering for a fork. |
| AIR-5 | No product workflow and terminology map | medium | `rejected` | Writing a product map for someone else's project would be inventing intent rather than recording it. |

## Codebase hygiene — 71/100

| ID | Finding | Sev | Status | Note |
|---|---|---|---|---|
| HYG-1 | Frontend has no lint, format or test commands | medium | `todo` | |
| HYG-2 | Public constructors overloaded with positional parameters (18 functions over 7) | medium | `rejected` | Converting `VerbatimRAG`, `VerbatimTransform` and the Milvus stores to keyword-only or config objects is a breaking change to the public API of an upstream library. Only meaningful as an upstream proposal. |
| HYG-3 | Empty and duplicated assets | low | `todo` | Overlaps DEAD-6. |
| HYG-4 | Notebook outputs carry the original author's home path | low | `todo` | `/Users/adamkovacs/...` in two notebooks under `docs/`. |
| HYG-5 | Deprecated `verbatim_rag/chunking.py` retained as compatibility debt | low | `rejected` | Same reason as DEAD-7. |

## Open-source readiness — 100/100

`n/a`. Domain no-op for a pure fork; all 14 criteria skipped. Nothing to close.

## Beyond the audit

Found while verifying the reports against the tree, and while writing the first
API test. None of these appear in any of the ten documents.

| ID | Finding | Status | Note |
|---|---|---|---|
| BEY-1 | `/api/query_async` returns 500 on every call | `done` | **How:** `APIService.query`/`query_async` now accept `filter` and `search_params` and forward them, matching what the route already passed. Two contract tests pin it; against the parent commit they fail with `assert 500 == 200`. **Why this way:** the alternative was to point the route at `rag.query_async` directly, as seven of the eight routes already do. That trades a signature fix for a change of which layer serves a request, with no user-visible benefit and a real behaviour risk. Which layer should own the request path is a design question for the maintainer, recorded under BEY-2. |
| BEY-2 | Two near-duplicate async endpoints, one broken | `todo` | `/api/query_async` goes through the service layer and fails; `/api/query/async` bypasses it and works. |
| BEY-3 | `rag.k` is not restored when a stream raises | `done` | **How:** the save-mutate-restore dance is gone rather than repaired — `self.rag.k` was read in exactly one place, so a local `k` replaces five mutation sites and the race cannot recur. **Why this way:** adding the missing restore to the outer `except` would have left four other paths and the concurrency bug intact; two simultaneous streams overwrote each other even when both succeeded. A regression test drives a failing stream and asserts the shared value is untouched. |
| BEY-4 | Retrieved text enters the extraction prompt as instruction, not data | `done` | **Scope corrected while fixing it.** The first write-up here claimed injection could make the model return spans that are not in the source. It cannot: `_verify_spans` checks every span against the text of the document it was attributed to, so fabrication *and* misattribution are already dropped, and the default path additionally embeds documents as JSON. **What actually survives verification is suppression** — a document that persuades the model to return an empty array for itself is indistinguishable from a document with nothing relevant, and a provenance product that silently omits a source is failing at exactly its job. **How:** both extraction prompts now fence retrieved text in explicit markers, say it is data rather than instruction, place the authoritative rules *after* the block, and state that a document asking to be skipped must still be reported. **Why this way — no sanitisation:** neutralising injection markers would rewrite the text the model is asked to quote, and any span containing a rewritten marker would then fail verbatim verification. On a corpus of papers that includes papers about prompt injection, that trades a speculative attack for certain data loss. **Limits, stated plainly:** the delimiter is forgeable, and structural tests prove the instruction is present, not that a model obeys it. The real guarantee remains span verification; this is defence in depth on top of it. |
| BEY-5 | `import api.app` raises whenever a `.env` holds `OPENAI_API_KEY` | `done` | Found by writing the first API test. `APIConfig` inherits pydantic-settings' default `extra="forbid"`, and `create_app()` calls `get_config()` at import time — so following the README (`cp .env.example .env`, add the key) makes `uvicorn api.app:app` fail before it serves anything. Docker hides it because `.dockerignore` drops `.env` and the values arrive as environment variables instead. **How:** `extra="ignore"`. **Why this way:** `.env` is shared with the rest of the stack by the README's own instructions, so unknown keys are expected input, not a configuration error. |
| BEY-6 | Every documented `API_*` environment variable was inert | `done` | `Field(..., env="API_HOST")` is a Pydantic v1 idiom; v2 keeps it as schema metadata only. Measured before the fix: `API_HOST=1.2.3.4` left `host=0.0.0.0`, while the undocumented `HOST=5.6.7.8` worked. **How:** `validation_alias`, which is v2's equivalent. **Why this way:** the alternative was to rename the fields to match the accidental names, which would have made the code true by changing the documented contract instead of honouring it. This deepens CFG-1: the settings were not merely disconnected from the run path, their names did nothing. |

## Review gate — API group

The planned gate was an independent review agent. Five attempts died with
`Connection lost mid-response`, at different steps and under two different
advisor models, so the review was done by hand instead. That is weaker: it is the
author checking his own work, and it is recorded as such. The remaining
independent gates are the evaluation run and the final multi-agent review.

Two things it changed:

- **A test was passing for the wrong reason.** `TestStreamingLeavesSharedStateAlone`
  set a `side_effect` on `index.query`, but the stream never reached it — the
  generator died earlier on `await` against a plain `MagicMock`, so the assertion
  held for a reason unrelated to `rag.k`. The fake now makes intent detection
  awaitable, retrieval is actually reached, and the test additionally asserts the
  `k` that was passed. Checked against the pre-fix `streaming.py`: it fails there
  with `99 != 5`, which it did not do before.
- **`extra="forbid"` covered the wrong route.** It was set on `QueryRequestModel`
  only, so `/api/query/stream` — the one the live UI actually calls — still
  accepted and ignored unknown fields, which is the exact defect DEAD-2 was about.
  Extended to `StreamQueryRequestModel` and to `VerbatimTransformRequest`, and
  deliberately *not* to `VerbatimContextItem`: that endpoint takes context from
  any RAG, and those items legitimately carry keys this code does not know.
  A test pins that the two fields the live UI sends are still accepted.

Worth noting how the first was found: the verification of it was itself wrong at
first. `git stash push` on an unmodified file returns success, so the `||`
fallback never ran and the "pre-fix" comparison was silently testing the current
code. Same class of error as the test it was checking.
