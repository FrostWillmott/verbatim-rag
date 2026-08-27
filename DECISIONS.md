# Decisions

Append-only log of non-obvious choices — not a changelog of every commit.
Newest entry at the top. See `documentation.md` in the rules-library for the
convention. Don't edit past entries; if a decision is reversed, add a new one
that supersedes it.

Scope: decisions about **this project** — its code, configuration, dependencies,
process. Decisions about the personal harness that happens to be checked in here
— which rule modules apply, how the linter preset was adapted, editor settings —
belong in their commit messages, not in this file. Someone reading this
repository wants to know why the software is the way it is.

<!--
## YYYY-MM-DD — <short title>
<One or two lines: the decision and why. Link related files/PRs if useful.>
-->

## 2026-08-27 — Retrieved text is framed as data, and deliberately not sanitised

Retrieved documents are attacker-controlled in any real deployment, and they were
interpolated into the extraction prompt with no delimiter and no statement of
what they are. In `extraction/default.txt` the rules came *before* the documents,
which is the worst order: an injected instruction gets to speak last.

The finding was narrower than it first looked, and the correction is worth
keeping. `_verify_spans` checks every span against the text of the document it
was attributed to, so a fabricated quote is dropped, and so is a quote
misattributed to another document. The verbatim guarantee holds under injection.
What does not hold is completeness: a document that persuades the model to return
an empty array for itself is indistinguishable from a document with nothing
relevant. For a product whose entire claim is provenance, silently omitting a
source is the failure that matters, and it is the one verification cannot see.

Both extraction prompts now fence the retrieved text, say plainly that it is data
rather than instruction, put the authoritative rules after the block, and state
that a document asking to be skipped must still be reported.

Sanitising the text was rejected. Neutralising injection markers rewrites the
text the model is asked to quote from, so any span containing a rewritten marker
fails verbatim verification against the original — on a corpus of ACL papers,
which includes papers about prompt injection, that trades a speculative attack
for certain, silent data loss.

Two limits, stated rather than implied: the delimiter is forgeable by a document
that contains it, and the tests assert the instruction is present, not that a
model obeys it. Proving the latter needs an evaluation set, which is a piece of
work in its own right. This is defence in depth on top of span verification, not
a replacement for it.

## 2026-08-27 — CI installs from the same pin set as everything else

The docs workflow ran `pip install mkdocs-material "mkdocstrings[python]>=0.24"`
in a job holding `contents: write`, which means a freshly published release of
any of those packages, or of anything they depend on, executed install-time code
in a job that can write to this repository. That was the audit's only critical
finding.

Closed by pointing every `pip install` in both workflows at
`dev-constraints.txt`, and by declaring the release and audit tooling — `build`,
`twine`, `pip-audit` — in the `dev` extra so one generated file covers local
work, CI and docs alike. The alternative was a second list of versions
maintained inside the workflow, which is the duplication this repository has
been removing all day.

Verified, not reviewed. The deploy job runs only on push to `main`, so it cannot
be exercised from a pull request; instead its exact install command was run
against a clean virtualenv with pip — the installer CI uses, not uv — and
resolved to the pinned `mkdocs-material 9.7.7`, `mkdocstrings 1.0.6`,
`mkdocs 1.6.1`. Worth stating plainly: version pinning prevents a fresh
compromised release from being pulled, but it is not hash verification.
`--generate-hashes` with `--require-hashes` is the next increment, not this one.

Actions are pinned to commit SHAs with the tag left as a trailing comment, on the
same reasoning: a tag is mutable and an action runs as code inside the workflow,
so it belongs in the same class as a package. `ubuntu-latest` stays floating on
purpose — it is GitHub-maintained, and pinning it buys maintenance work rather
than supply-chain safety. The `contents: write` permission also stays, because
`mkdocs gh-deploy` needs it; what changed is that it no longer sits next to
unpinned third-party install code.

## 2026-08-27 — Request cost is capped by literals, and shared state is no longer written

`num_docs` and `k` are bounded to 1–50, the transform context to 100 items of
100 000 characters. The numbers are literals in `api/app.py`, deliberately not
new environment settings: the previous change removed options that were declared
and did nothing, and an unwired `MAX_NUM_DOCS` would have recreated exactly that.
When someone needs to tune these, they become settings and get wired in the same
change.

The cost was measured rather than assumed. A request carrying 10 000 context
items kept the endpoint working for 41 seconds; with the cap it is refused in
0.03 seconds.

`StreamingRAG` no longer writes to `self.rag.k` at all. It had been saving the
value, overwriting it with the caller's `num_docs`, and restoring it at five
different exit points — one of which, the outer `except`, did not restore, so a
failed stream left the retrieval default rewritten for every later request in
the process. Repairing that path would have left the other problem standing:
`self.rag` is a singleton, so two concurrent streams corrupted each other even
when both succeeded. `self.rag.k` turned out to be read in exactly one place, so
a local variable replaces the whole mechanism.

The LLM key is now reported instead of guessed at. The old check asked whether
`OPENAI_API_KEY` was present in the environment, not whether it held anything,
while `.env.example` ships it empty — so the most likely broken setup was also
the one that produced no warning. Blank now counts as missing, the message goes
through the logger rather than `print` at import time, and `/api/status` carries
`llm_configured` so the state is visible before the first query instead of after
it. It is still not a startup failure: `.env.example` documents on purpose that a
missing key does not stop the stack. The defect was the silence, not the
tolerance.

## 2026-08-27 — Three identical-looking settings got three different answers

`MAX_QUESTION_LENGTH`, `TEMPLATES_PATH` and `template_id` were all reported as
"declared but detached". They are not the same problem.

The first two had a consumer to connect to, so they were connected.
`MAX_QUESTION_LENGTH` now reaches `APIService`, which previously hardcoded
`1000` and did not receive the config at all. `TEMPLATES_PATH` now loads into the
template manager that actually renders answers, instead of only the separate one
behind `/api/templates`.

`template_id` had no consumer anywhere: neither `VerbatimRAG.query` nor
`query_async` accepts such a parameter, so honouring it would mean changing the
public API of the upstream library — not a fork owner's call. It is removed from
the schema instead, and `QueryRequestModel` now forbids extra fields, so a client
that sends it gets a 422 rather than a 200 with an answer that ignored it.
Silence was the defect; rejecting is the fix.

The obvious way to wire `TEMPLATES_PATH` would have been to hand the API's
existing `TemplateManager` to `VerbatimRAG`, which accepts one. That would have
been a regression: the API builds it with no `llm_client`, and a manager without
one has `strategies["contextual"] is None`, so the mode falls back to `static`
and the framing of every answer changes silently. There is a test pinning that
behaviour, because it is the reason for the shape of the code.

`API_HOST` and `API_PORT` stay direct-run-only. The container's entrypoint gives
uvicorn its host and port; making the Dockerfile read these would move deployment
configuration into the image for no gain. That is a decision, not an oversight,
so it is written down rather than left looking like the same bug.

## 2026-08-27 — Secret files are blocked by an enforced rule, not a declared one

Reads of `.env`, `*.local` env files, `*.pem` and `*.key` are denied in
`.claude/settings.json`. Verified rather than assumed: after the change the
refusal comes back through both the file tool and Bash, which were the two routes
that had in fact been reading `.env` earlier the same day.

The repository previously carried a `.aiignore` listing the same paths, and it
was deleted. Nothing here consumed it, so it enforced nothing while looking like
a guarantee — and two mechanisms for one job is the failure this repository's own
rules forbid. `.env.example` stays readable: it is a tracked template the README
points at and holds no secret.

## 2026-08-27 — The first API test was written before the fix it proves

`/api/query_async` answered 500 to every request: the route passed `filter` and
`search_params` to a service method whose signature accepted neither, and a broad
`except Exception` turned the `TypeError` into a generic server error. The two
contract tests that pin the correct behaviour were written first and committed
together with the fix, so `make check` stays green at every commit while the
evidence survives: check out the parent commit's `api/` and both fail with
`assert 500 == 200`.

The fix is the signature, not the routing. Seven of the eight routes already
bypass `APIService` and call `rag.*` directly, so the tempting change was to make
the eighth match them — but that swaps which layer serves a request for no
user-visible gain, and the service layer's fate is a design question for the
maintainer, not a side effect of a bug fix.

The test fixtures build `APIConfig(_env_file=None)` on purpose. A suite whose
result depends on the developer's own `.env` is not a suite.

## 2026-08-27 — The documented local setup could not start the API at all

Trying to write the first API test surfaced two defects nobody had gone looking
for, neither of them in any of the ten reports.

`APIConfig` inherited pydantic-settings' default `extra="forbid"`, and
`create_app()` calls `get_config()` at import time rather than through dependency
injection. So a `.env` containing `OPENAI_API_KEY` — the file the README
instructs you to create — made `import api.app` raise outright, before any
request. Docker never showed it: `.dockerignore` drops `.env`, so the values
arrive as environment variables, which pydantic-settings does not police the same
way.

Separately, every `Field(..., env="API_HOST")` was a Pydantic v1 idiom that v2
keeps only as schema metadata. Measured before the change: `API_HOST=1.2.3.4`
left `host` at `0.0.0.0`, while the undocumented `HOST=5.6.7.8` worked. The
`API_*` names were inert; the ones that happened to work did so only because the
field name matched.

Both were fixed by honouring the documented contract — `extra="ignore"` because
`.env` is shared with the rest of the stack by the README's own instructions, and
`validation_alias` because it is v2's equivalent of what the author meant. The
alternative, renaming fields to match the accidental names, would have made the
code true by quietly changing the contract instead of keeping it.

This deepens CFG-1 rather than closing it: the finding said the settings do not
reach the run path, and it turns out their names did nothing either.

## 2026-08-27 — Fork status recorded in the repository, not only in correspondence

The premise of this work — that the audited findings describe upstream code — was
explained by mail to the recruiter, which is the wrong place for it to live: the
person who reviews the code is not the person who received the message. It now
sits in the `Premise` section of `AUDIT.md` and will be repeated in the pull
request description, which is what a reviewer opens first.

No separate file for it. A fourth document beside `AUDIT.md`, `DECISIONS.md` and
the rules directory would split one piece of context three ways.

The section is kept to verifiable facts — the audited commit, the fork chain, the
platform counters — rather than to argument. As repository context it lets a
reader reach the conclusion themselves; written as a defence it would invite
scepticism about the rest of the register.

This closes CD-3, which asks for a repository-side note naming the authoritative
source and where local divergence is recorded.

## 2026-08-27 — Dependency pinning follows the repository's existing lock idiom

The root manifests had no pinned set, so local and CI installs resolved afresh
on every run — the dependency audit raises this as its third improvement step.
Closed with `dev-constraints.txt`, generated by `make lock` and consumed by
`make install` as `pip install -c`.

The mechanism matches what the repository already does rather than what I would
reach for by default. `docker/overrides.txt` documents
`uv pip compile … -o docker/constraints.txt`, and the Dockerfile installs with
`pip install -c docker/constraints.txt`: the project already treats uv as the
resolver and pip as the installer. `dev-constraints.txt` is that same pattern
applied to the development set.

A first attempt used `uv.lock` with `uv sync`, and was reverted before leaving
the branch. Two things were wrong with it. Pip cannot parse `uv.lock` and CI
installs with pip, so the lock would have pinned my machine and nothing that is
actually built — the determinism the audit asks for would have been decorative.
And `uv sync` takes ownership of `.venv`, pruning whatever the lock omits;
adopting it moved about forty packages in an environment that was working.

Tool versions are declared once, in the `dev` extra of `pyproject.toml`, and
resolved once, in `dev-constraints.txt`. The ruff pre-commit hooks call
`.venv/bin/ruff` rather than a `rev:`-pinned mirror, so the hook and `make lint`
cannot end up enforcing different rule sets.

`[tool.uv.sources]` points `verbatim-core` at `packages/core/`. Without it the
compile pins the published 0.2.8, which then fights the editable install that
CI, the Dockerfile and `make install` all depend on. It has a side effect worth
knowing about: `docker/constraints.txt` currently pins `verbatim-core==0.2.8`
because it predates this key, so the next regeneration of that file will drop
the pin. Noted in `pyproject.toml` next to the key.

Known gap: CI still installs its tools unpinned and reads neither constraints
file. Wiring it up closes the rest of this finding and part of the critical
supply-chain one; it belongs to that work, not to this change.

## 2026-08-27 — `make check` has no type-checking step (TODO)

The verification gate is lint + format + tests. Type checking is deliberately
absent: mypy is declared in no manifest, there is no `[tool.mypy]` section, and
the inherited code has never been type-checked, so the step would be red from the
first commit and stay red. A gate that can never pass trains everyone to ignore
it. `make typecheck` prints a pointer to this entry rather than lying about what
it ran.

On a project I owned this would be a tracked task, not a deferral. Doing it
properly means: add mypy to the dev extra, start from a non-strict
`[tool.mypy]`, exclude the modules that depend on untyped third-party packages
(`torch`, `transformers`, `pymilvus`), and tighten per-package from there. That
is a work item of its own, not a side effect of installing a harness.

## 2026-08-27 — The lint gate stays where the project already had it

A stricter preset was measured against this tree before being considered: 11 rule
groups, line-length 88, target py312 produced **838 errors and 52 of 73 files
under reformatting, against an upstream baseline of zero**. The bulk is
pyupgrade (~235), bugbear (28) and ruff-specific (14) — a mass rewrite of code
this fork did not write, which would bury every real change in the diff.

So the configuration stays as the project had it and stays in `pyproject.toml`.
A standalone `ruff.toml` is not added: ruff discovers it first and then ignores
`[tool.ruff]` entirely rather than merging, so it would create a silent conflict
where none existed. There is now a note next to the block saying so.

Two additions only. `ASYNC`, which reports nothing today and guards a codebase
that genuinely mixes sync and async paths. And `known-first-party`, because
`verbatim_core` lives under `packages/core/`, is invisible to ruff's `src`
inference and was being sorted as a third-party package; the 11 `I001`
violations that surfaced are closed with the autofixer.

Those 11 files are the one place inherited code was touched, and the line is
deliberate: import ordering has a provably correct fixer, unlike the semantic
rewrites the wider rule set would have produced. For the same reason the commit
hooks run against the staged set only — repo-wide they would rewrite 68
inherited files on whitespace alone, plus 3 more that ruff reformats in
`examples/` and `scripts/`.

`target-version` stays at `py310`: both manifests declare `requires-python
>=3.10` and CI runs a 3.10/3.11/3.12 matrix, so a newer target would let
pyupgrade emit syntax that breaks the oldest leg.

## 2026-08-27 — Audit remediation lives on a branch that is never merged

Work on the external code audit happens on `audit-remediation`, branched from
`main` at `88f510a` — the exact commit the audits were taken against, so every
finding is reproducible from the branch point. `main` stays byte-identical to
`upstream/main` so that future contributions to `KRLabsOrg/verbatim-rag` can
still branch cleanly from it. A draft pull request into `main` is opened for CI
only: both workflows filter on `branches: [main]`, so without an open PR against
`main` nothing on this branch would ever be checked.
